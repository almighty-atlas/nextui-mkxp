#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline, host-only regression tests. No compiler, downloader or target run."""
import copy
import io
import os
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import issue_26_sandbox as gate


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.records = {'true': gate.tool_record('/usr/bin/true', 'test host tool')}
        gate.farm(self.root/'tools', self.records)
        self.env = gate.environment(self.root, self.root/'tools')

    def reject_environment(self, key, value='hostile'):
        env = dict(self.env, **{key: value})
        with self.assertRaises((ValueError, FileNotFoundError)):
            gate.checked_run(['/usr/bin/true'], self.root, env, self.records,
                             self.root/'logs', 'must-not-run')
        self.assertFalse((self.root/'logs').exists())

    def test_parent_environment_is_not_inherited(self):
        keys = ['LD_PRELOAD','LD_LIBRARY_PATH','LD_AUDIT','LD_DEBUG','PYTHONPATH',
                'GCC_EXEC_PREFIX','COMPILER_PATH','CPATH','C_INCLUDE_PATH',
                'CPLUS_INCLUDE_PATH','LIBRARY_PATH','PKG_CONFIG_PATH',
                'PKG_CONFIG','BASH_ENV','ENV','HOME','HTTPS_PROXY','TOKEN','CTNG_LD_IS']
        with patch.dict(os.environ, {k:'hostile' for k in keys}):
            env = gate.environment(self.root,self.root/'tools')
        for key in keys:self.assertNotIn(key,env)
        self.assertEqual(env['LC_ALL'],'C')
        self.assertEqual(env['LANG'],'C')
        self.assertEqual(env['TMPDIR'],str(self.root/'tmp'))

    def test_native_child_receives_only_fresh_environment(self):
        records={'env':gate.tool_record('/usr/bin/env','native environment probe')}
        farm=self.root/'env-tools';gate.farm(farm,records)
        with patch.dict(os.environ,{'LD_PRELOAD':'/never-load-this.so','LD_AUDIT':'/never-audit.so',
                                    'HOSTILE_TOKEN':'must-not-reach-child'}):
            env=gate.environment(self.root,farm)
            result=gate.checked_run(['/usr/bin/env'],self.root,env,records,self.root/'logs','native-env')
        self.assertEqual(result['exit_code'],0)
        output=(self.root/'logs/native-env.log').read_text()
        for text in ('LD_PRELOAD','LD_AUDIT','HOSTILE_TOKEN','must-not-reach-child','HOME='):
            self.assertNotIn(text,output)
        self.assertIn('LC_ALL=C',output)

    def test_injected_environment_rejected_before_execution(self):
        for key in ['LD_PRELOAD','LD_LIBRARY_PATH','LD_AUDIT','LD_DEBUG',
                    'PYTHONPATH','HOME','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH',
                    'GCC_EXEC_PREFIX','COMPILER_PATH','LIBRARY_PATH',
                    'PKG_CONFIG_PATH','PKG_CONFIG','BASH_ENV','ENV','HTTPS_PROXY','CTNG_LD_IS']:
            with self.subTest(key=key):self.reject_environment(key)

    def test_temporary_directory_rejected(self):self.reject_environment('TMPDIR','/tmp')
    def test_pkg_config_directory_rejected(self):self.reject_environment('PKG_CONFIG_LIBDIR','/usr/lib/pkgconfig')

    def test_locale_rejected(self):self.reject_environment('LC_ALL','de_DE.UTF-8')
    def test_path_injection_rejected(self):self.reject_environment('PATH',str(self.root/'tools')+':/usr/bin')
    def test_unknown_compiler_environment_rejected(self):self.reject_environment('CC','/usr/bin/false')

    def test_unknown_farm_entry_rejected(self):
        (self.root/'tools/curl').symlink_to('/usr/bin/true')
        with self.assertRaises(ValueError):gate.validate_environment(self.env,self.records)

    def test_changed_farm_symlink_rejected(self):
        p=self.root/'tools/true';p.unlink();p.symlink_to('/usr/bin/false')
        with self.assertRaises(ValueError):gate.validate_environment(self.env,self.records)

    def test_unknown_initial_executable_rejected(self):
        with self.assertRaises(ValueError):
            gate.checked_run(['/usr/bin/false'],self.root,self.env,self.records,self.root/'logs','unknown')

    def test_unknown_wrapper_rejected(self):
        p=self.root/'wrapper';p.write_text('#!/bin/sh\nexit 0\n')
        with self.assertRaises(ValueError):gate.tool_record(p,'untrusted wrapper')

    def test_target_executable_is_not_host_tool(self):
        p=self.root/'aarch64';p.write_bytes(b'\x7fELF\x02\x01'+b'\0'*12+struct.pack('<H',183))
        with self.assertRaises(ValueError):gate.tool_record(p,'must not execute')

    def test_hash_and_resolved_root_required(self):
        p=self.root/'input';p.write_bytes(b'approved')
        digest=gate.sha256(p)
        self.assertEqual(gate.check_file(p,digest,[self.root]),p)
        p.write_bytes(b'changed')
        with self.assertRaises(ValueError):gate.check_file(p,digest,[self.root])
        q=self.root/'link';q.symlink_to('/usr/bin/true')
        with self.assertRaises(ValueError):gate.check_file(q,gate.sha256(q),[self.root])

    def test_host_include_and_symlink_escape_rejected(self):
        with self.assertRaises(ValueError):gate.validate_search_paths(['/usr/include'],[self.root])
        p=self.root/'include';p.symlink_to('/usr/include')
        with self.assertRaises(ValueError):gate.validate_search_paths([p],[self.root])

    def archive(self,members):
        p=self.root/'test.tar'
        with tarfile.open(p,'w') as tf:
            for name,kind,target in members:
                m=tarfile.TarInfo(name);m.mtime=1234
                if kind=='file':m.size=1;tf.addfile(m,io.BytesIO(b'x'))
                else:m.type=kind;m.linkname=target;tf.addfile(m)
        return p

    def test_archive_negatives(self):
        cases=[('../escape','file',''),('/absolute','file',''),
               ('link',tarfile.SYMTYPE,'../../escape'),
               ('link',tarfile.SYMTYPE,'/absolute'),
               ('hard',tarfile.LNKTYPE,'file'),('fifo',tarfile.FIFOTYPE,'')]
        for i,member in enumerate(cases):
            with self.subTest(member=member):
                p=self.archive([member])
                with self.assertRaises(ValueError):gate.extract(p,gate.sha256(p),self.root/f'out{i}')

    def test_archive_symlink_ancestor_and_duplicate_rejected(self):
        for i,members in enumerate([
            [('a',tarfile.SYMTYPE,'inside'),('a/file','file','')],
            [('file','file',''),('file','file','')]]):
            p=self.archive(members)
            with self.assertRaises(ValueError):gate.extract(p,gate.sha256(p),self.root/f'out{i}')

    def test_archive_composite_symlink_escape_and_cycle(self):
        for i,members in enumerate([
            [('alias',tarfile.SYMTYPE,'.'),('escape',tarfile.SYMTYPE,'alias/..')],
            [('a',tarfile.SYMTYPE,'b'),('b',tarfile.SYMTYPE,'a')]]):
            p=self.archive(members)
            with self.assertRaises(ValueError):gate.extract(p,gate.sha256(p),self.root/f'chain{i}')

    def test_archive_hash_before_parse_and_generated_mtime(self):
        p=self.archive([('file','file','')])
        with self.assertRaises(ValueError):gate.extract(p,'0'*64,self.root/'bad')
        gate.extract(p,gate.sha256(p),self.root/'good')
        self.assertEqual((self.root/'good/file').stat().st_mtime,1234)

    def test_malformed_elf_and_readelf_provenance(self):
        p=self.root/'bad';p.write_bytes(b'not ELF')
        with self.assertRaises(ValueError):gate.elf_facts(p,'/usr/bin/readelf',self.env,self.records)
        records={'readelf':gate.tool_record('/usr/bin/readelf','test native readelf')}
        farm=self.root/'readelf-tools';gate.farm(farm,records);env=gate.environment(self.root,farm)
        with self.assertRaises(ValueError):gate.elf_facts(p,'/usr/bin/readelf',env,records)


    def test_compiler_tree_requires_complete_known_inventory(self):
        p=self.archive([('compiler/input','file','')])
        gate.extract(p,gate.sha256(p),self.root/'compiler-extract')
        self.assertEqual(gate.verify_archive_tree(p,gate.sha256(p),self.root/'compiler-extract'),1)
        (self.root/'compiler-extract/unknown').write_text('unexpected')
        with self.assertRaises(ValueError):
            gate.verify_archive_tree(p,gate.sha256(p),self.root/'compiler-extract')

    def test_compiler_hardlink_cannot_be_replaced_by_symlink(self):
        archive=self.archive([('file','file',''),('alias',tarfile.LNKTYPE,'file')])
        root=self.root/'compiler';root.mkdir();(root/'file').write_bytes(b'x')
        os.link(root/'file',root/'alias')
        self.assertEqual(gate.verify_archive_tree(archive,gate.sha256(archive),root),2)
        (root/'alias').unlink();(root/'alias').symlink_to('file')
        with self.assertRaises(ValueError):gate.verify_archive_tree(archive,gate.sha256(archive),root)

    def test_archive_internal_symlink_is_preserved(self):
        p=self.archive([('folder/data','file',''),('alias',tarfile.SYMTYPE,'folder/data')])
        gate.extract(p,gate.sha256(p),self.root/'safe')
        self.assertTrue((self.root/'safe/alias').is_symlink())
        self.assertEqual((self.root/'safe/alias').read_bytes(),b'x')

    def test_conflicting_kernel_notes_rejected(self):
        import subprocess
        p=self.root/'elf'
        p.write_bytes(b'\x7fELF\x02\x01'+b'\0'*10+struct.pack('<HH',2,183))
        records={'readelf':gate.tool_record('/usr/bin/readelf','test native readelf')}
        farm=self.root/'readelf-tools';gate.farm(farm,records);env=gate.environment(self.root,farm)
        result=subprocess.CompletedProcess([],0,'OS: Linux, ABI: 4.9.0\nOS: Linux, ABI: 4.19.0','')
        with patch.object(gate.subprocess,'run',return_value=result):
            with self.assertRaises(ValueError):gate.elf_facts(p,'/usr/bin/readelf',env,records)

    def test_version_definitions_are_not_requirements(self):
        import subprocess
        p=self.root/'elf'
        p.write_bytes(b'\x7fELF\x02\x01'+b'\0'*10+struct.pack('<HH',2,183))
        records={'readelf':gate.tool_record('/usr/bin/readelf','test native readelf')}
        farm=self.root/'readelf-tools';gate.farm(farm,records);env=gate.environment(self.root,farm)
        output=("Version definition section '.gnu.version_d' contains 1 entry:\n"
                "  Name: GLIBC_2.28\n"
                "Version needs section '.gnu.version_r' contains 1 entry:\n"
                "  Name: GLIBC_2.17\n")
        with patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],0,output,'')):
            facts=gate.elf_facts(p,'/usr/bin/readelf',env,records)
        self.assertEqual(facts['required_versions'],['GLIBC_2.17'])


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.facts={'machine':183,'type':2,'interpreter':'/lib/ld-linux-aarch64.so.1',
                    'gnu_linux_abi':'4.9.0','needed':['libc.so.6'],'rpaths':[],
                    'required_versions':['GLIBC_2.17']}

    def errors(self,**changes):
        facts=copy.deepcopy(self.facts);facts.update(changes)
        return gate.policy_errors(facts,'4.9','2.28',['libc.so.6'])

    def test_valid_static_probe(self):self.assertEqual(self.errors(),[])
    def test_kernel_mismatch(self):self.assertIn('kernel baseline too high',self.errors(gnu_linux_abi='4.19.0'))
    def test_glibc_floor(self):self.assertIn('GLIBC requirement too high',self.errors(required_versions=['GLIBC_2.29']))
    def test_private_cxx_version(self):self.assertTrue(self.errors(required_versions=['GLIBC_PRIVATE','GLIBCXX_3.4']))
    def test_rpath_and_needed(self):
        self.assertTrue(self.errors(rpaths=['/tmp/host']))
        self.assertTrue(self.errors(needed=['libc.so.6','libUnexpected.so']))
    def test_missing_kernel_note(self):self.assertTrue(self.errors(gnu_linux_abi=None))
    def test_malformed_facts(self):
        for change in [{'gnu_linux_abi':'4..9'},{'required_versions':['GLIBC_2..17']},
                       {'required_versions':[None]},{'needed':'libc.so.6'},
                       {'required_versions':None},{'machine':62},{'type':1},
                       {'interpreter':'/lib64/ld-linux-x86-64.so.2'},{'interpreter':None}]:
            with self.subTest(change=change):self.assertTrue(self.errors(**change))
        self.assertTrue(gate.policy_errors(None,'4.9','2.28',[]))


if __name__=='__main__':unittest.main()
