"""Offline deterministic archive/ELF policy tests; no target execution/download."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import h700_build_gate as gate
import h700_triangle_crosscheck as build

READELF = '''ELF Header:
 Class: ELF64
 Machine: AArch64
 [Requesting program interpreter: /lib/ld-linux-aarch64.so.1]
 0x1 (NEEDED) Shared library: [libc.so.6]
Version definition section '.gnu.version_d' contains 1 entry:
 Name: GLIBC_99.0
Version needs section '.gnu.version_r' contains 1 entry:
 0x0010: Name: GLIBC_2.17 Flags: none Version: 2
Displaying notes found in: .note.ABI-tag
 OS: Linux, ABI: 3.7.0
'''
POLICY = {'interpreter':'/lib/ld-linux-aarch64.so.1','allowed_needed':['libc.so.6'],
          'max_glibc':'2.17','allowed_rpaths':[],'kernel':'4.9.170'}


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def archive(self, entries):
        p=self.root/'input.tar'
        with tarfile.open(p,'w') as t:
            for name,kind,target in entries:
                m=tarfile.TarInfo(name);m.mode=0o7777
                if kind=='file':
                    data=target.encode();m.size=len(data);t.addfile(m,io.BytesIO(data))
                elif kind=='dir':m.type=tarfile.DIRTYPE;t.addfile(m)
                else:
                    m.type={'sym':tarfile.SYMTYPE,'hard':tarfile.LNKTYPE,'device':tarfile.CHRTYPE}[kind]
                    m.linkname=target;t.addfile(m)
        return p,gate.sha256(p)

    def facts(self):
        result=gate.parse_readelf(READELF)
        result.update({'class':64,'endian':'little','type':2,'machine':183})
        return result

    def test_digest_format_and_mismatch_before_writes(self):
        for value in ('UNKNOWN','A'*64,'a'*63):
            with self.assertRaises(ValueError):gate.digest(value)
        p,h=self.archive([('file','file','data')])
        with self.assertRaises(ValueError):gate.safe_extract(p,'0'*64,self.root/'dest')
        self.assertFalse((self.root/'dest').exists())

    def test_safe_files_and_relative_links(self):
        p,h=self.archive([('usr/lib/real','file','data'),('usr/lib/alias','sym','real'),
                          ('usr/copy','hard','usr/lib/real')])
        gate.safe_extract(p,h,self.root/'dest')
        self.assertEqual((self.root/'dest/usr/lib/alias').read_text(),'data')
        self.assertEqual((self.root/'dest/usr/copy').read_text(),'data')
        self.assertEqual((self.root/'dest/usr/lib/real').stat().st_mode & 0o7022,0)
        with self.assertRaises(ValueError):gate.safe_extract(p,h,self.root/'dest')

    def test_archive_escape_special_duplicate_and_link_ancestors(self):
        cases=[[('../escape','file','x')],[('/absolute','file','x')],
               [('bad','sym','../../escape')],[('bad','sym','/absolute')],
               [('node','device','')],[('file','file','x'),('file','file','x')],
               [('dir','sym','target'),('dir/file','file','x')],
               [('bad','hard','absent')]]
        for entries in cases:
            with self.subTest(entries=entries):
                p,h=self.archive(entries)
                with self.assertRaises(ValueError):gate.safe_extract(p,h,self.root/'dest')
                self.assertFalse((self.root/'dest').exists())

    def test_explicit_subset_omits_unrelated_unsafe_links(self):
        p,h=self.archive([('usr/bin/config','sym','/external/build/tool'),
                          ('usr/include/header.h','file','header')])
        with self.assertRaises(ValueError):gate.archive_members(p,h)
        gate.safe_extract(p,h,self.root/'dest',['usr/include'])
        self.assertFalse((self.root/'dest/usr/bin').exists())
        self.assertTrue((self.root/'dest/usr/include/header.h').is_file())

    def test_elf_parser_separates_required_versions_from_definitions(self):
        f=self.facts()
        self.assertEqual(f['required_versions'],['GLIBC_2.17'])
        self.assertEqual(f['gnu_linux_abi'],'3.7.0')
        self.assertEqual(gate.evaluate(f,POLICY),[])

    def test_fail_closed_unknown_target_and_kernel_mismatch(self):
        f=self.facts()
        self.assertTrue(gate.evaluate(f,{}))
        f['gnu_linux_abi']='4.19.0'
        self.assertIn('GNU Linux ABI note exceeds observed kernel',gate.evaluate(f,POLICY))

    def test_foreign_abi_versions_dependencies_and_rpaths(self):
        cases=[('machine',62,'not ELF64'),('class',32,'not ELF64'),
               ('endian','big','not ELF64'),('interpreter','/lib64/ld-linux-x86-64.so.2','interpreter mismatch'),
               ('needed',['libhost.so'],'unexpected NEEDED'),('rpaths',['/usr/local/lib'],'unexpected RPATH'),
               ('required_versions',['GLIBC_2.34'],'above approved floor'),
               ('required_versions',['GLIBC_PRIVATE'],'unreviewed GLIBC'),
               ('required_versions',['GLIBCXX_3.4.29'],'unexpected C++')]
        for key,value,expected in cases:
            with self.subTest(key=key,value=value):
                f=self.facts();f[key]=value
                self.assertTrue(any(expected in e for e in gate.evaluate(f,POLICY)))

    def test_policy_types_are_not_silently_coerced(self):
        for key,value in [('allowed_needed','libc.so.6'),('max_glibc','UNKNOWN'),('kernel',[]),('interpreter',123)]:
            p=copy.deepcopy(POLICY);p[key]=value
            with self.assertRaises(ValueError):gate.evaluate(self.facts(),p)

    def test_scanner_reads_metadata_without_execution(self):
        p=self.root/'fixture.elf';head=bytearray(20);head[:6]=b'\x7fELF\x02\x01';struct.pack_into('<HH',head,16,2,183);p.write_bytes(head)
        with patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],0,READELF,'')) as run:
            r=gate.scan_elf(p,POLICY)
            self.assertEqual(r['status'],'STATIC_POLICY_MATCH_ONLY')
            self.assertEqual(run.call_args.args[0][0],'readelf')
            self.assertIn('--notes',run.call_args.args[0])
        with patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','bad')):
            with self.assertRaises(ValueError):gate.scan_elf(p,POLICY)
        p.write_bytes(b'bad')
        with self.assertRaises(ValueError):gate.scan_elf(p,POLICY)

    def test_real_host_elf_cannot_receive_target_policy_match(self):
        # Read only the native shell's metadata, never execute it as an input.
        f=gate.scan_elf('/bin/sh',POLICY)
        self.assertEqual(f['status'],'BLOCKED')

    def test_runner_preflight_failure_never_executes_compiler(self):
        lock={'compiler':{'sha256':'0'*64}}
        with patch.object(build,'archive_members',side_effect=ValueError('SHA256 mismatch')):
            with patch.object(build.subprocess,'run') as run:
                with self.assertRaises(ValueError):build.run_build('bad','bad','bad',self.root/'out',lock,{})
                run.assert_not_called()
        self.assertFalse((self.root/'out').exists())

    def test_checked_in_lock_pins_and_unknown_target_are_explicit(self):
        lock=json.loads((ROOT/'docs/build/h700-inputs.lock.json').read_text())
        for item in ('compiler','sdk','triangle'):gate.digest(lock[item]['sha256'])
        for pin in [lock['triangle']['commit'],lock['compiler']['release_commit'],*lock['source_refs'].values()]:
            self.assertRegex(pin,r'^[a-f0-9]{40}$')
        self.assertIsNone(lock['sdk']['upstream_digest'])
        self.assertTrue(all(v is None for v in lock['installed_h700_runtime'].values()))
        target=json.loads((ROOT/'docs/build/h700-target-policy.json').read_text())
        self.assertTrue(gate.evaluate(self.facts(),target))
        # Scope protects against accidentally committing downloaded ELF/archive bytes.
        for folder in (ROOT/'docs/build',ROOT/'scripts'):
            for p in folder.rglob('*'):
                if p.is_file():
                    self.assertNotEqual(p.read_bytes()[:4],b'\x7fELF',str(p))
                    self.assertNotIn(p.suffix,('.xz','.tgz','.so','.a','.zip'))


if __name__=='__main__':unittest.main()
