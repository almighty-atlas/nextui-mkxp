import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import issue_26_gate as gate


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('home', 'tmp', 'host-bin'):
            (self.root / name).mkdir()
        self.policy = {'kernel': '4.9.170', 'max_glibc': '2.28',
                       'interpreter': '/lib/ld-linux-aarch64.so.1',
                       'needed': ['libc.so.6']}
        self.facts = {'abi': [64, 'little', 183], 'type': 2,
                      'interpreters': ['/lib/ld-linux-aarch64.so.1'],
                      'needed': ['libc.so.6'], 'rpaths': [],
                      'versions': ['GLIBC_2.17'], 'kernel_notes': ['4.9.0']}

    def test_complete_experimental_policy(self):
        self.assertEqual(gate.evaluate(self.facts, self.policy), [])

    def test_kernel_note_all_notes_checked(self):
        for notes in ([], ['4.19.0'], ['4.9.0', '4.19.0']):
            with self.subTest(notes=notes):
                self.assertTrue(gate.evaluate(dict(self.facts, kernel_notes=notes), self.policy))

    def test_symbol_floor_and_unknown_namespaces(self):
        for v in ('GLIBC_2.29', 'GLIBC_PRIVATE', 'GLIBCXX_3.4', 'CXXABI_1.3', 'OTHER_1'):
            with self.subTest(v=v):
                try:
                    errors = gate.evaluate(dict(self.facts, versions=[v]), self.policy)
                except ValueError:
                    continue
                self.assertTrue(errors)
        self.assertTrue(gate.evaluate(dict(self.facts, versions=[]), self.policy))

    def test_interpreter_needed_rpath_and_host_abi(self):
        for key, value in (('abi', [64, 'little', 62]), ('type', 1),
                           ('interpreters', []), ('needed', []),
                           ('needed', ['libc.so.6', 'libIMGegl.so']),
                           ('rpaths', ['']), ('rpaths', ['/usr/lib'])):
            with self.subTest(key=key, value=value):
                self.assertTrue(gate.evaluate(dict(self.facts, **{key: value}), self.policy))

    def test_malformed_unknown_policy(self):
        for p in ({}, None, dict(self.policy, kernel=None),
                  dict(self.policy, max_glibc='2.28evil'),
                  dict(self.policy, needed='libc.so.6'),
                  dict(self.policy, needed=[None]), dict(self.policy, extra=True)):
            with self.subTest(policy=p), self.assertRaises(ValueError):
                gate.evaluate(self.facts, p)

    def test_version_definitions_are_not_requirements(self):
        text = '''Version definition section '.gnu.version_d':
  Name: GLIBC_99.0
Version needs section '.gnu.version_r':
  Name: GLIBC_2.17
Version symbols section '.gnu.version':
  Name: GLIBC_PRIVATE
    OS: Linux, ABI: 4.9.0
    OS: Linux, ABI: 4.19.0
'''
        facts = gate.parse_readelf(text)
        self.assertEqual(facts['versions'], ['GLIBC_2.17'])
        self.assertEqual(facts['kernel_notes'], ['4.9.0', '4.19.0'])

    def test_hostile_environment_not_inherited_by_child(self):
        hostile = {n: '/unreviewed' for n in (
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT', 'LD_DEBUG', 'PYTHONPATH',
            'GCC_EXEC_PREFIX', 'COMPILER_PATH', 'CPATH', 'C_INCLUDE_PATH',
            'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'PKG_CONFIG_PATH',
            'PKG_CONFIG_LIBDIR', 'PKG_CONFIG_SYSROOT_DIR', 'CC', 'CXX',
            'CONFIG_SITE', 'BASH_ENV', 'ENV', 'MAKEFLAGS', 'PATH', 'HOME',
            'TMPDIR', 'LANG', 'LC_ALL', 'HTTPS_PROXY')}
        with patch.dict(os.environ, hostile):
            env = gate.clean_environment(self.root)
            self.assertNotIn('HOME', env)
            # Set hostile values only in the parent after Python has started.
            # This does not claim protection against pre-start loader injection.
            result = subprocess.run([sys.executable, '-I', '-c',
                                     'import os,json;print(json.dumps(dict(os.environ)))'],
                                    env=env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), env)

    def test_unknown_digest_changed_file_and_traversal(self):
        p = self.root / 'input'; p.write_bytes(b'source')
        digest = gate.sha256(p)
        self.assertEqual(gate.verified_file(self.root, 'input', digest), p)
        for relative, expected in (('input', None), ('input', '0' * 64),
                                   ('../input', digest), (str(p), digest)):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                gate.verified_file(self.root, relative, expected)

    def test_unsafe_symlinks_and_special_input(self):
        p = self.root / 'source'; p.write_text('source')
        (self.root / 'link').symlink_to(p)
        (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
        for relative in ('link', 'alias/source', 'home'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                gate.verified_file(self.root, relative, gate.sha256(p))
        (self.root / 'tmp').rmdir(); (self.root / 'tmp').symlink_to(self.root / 'home')
        with self.assertRaises(ValueError):
            gate.clean_environment(self.root)

    def test_unreviewed_search_paths_and_symlink_escape(self):
        gate.verify_search_paths([str(self.root / 'include')], [self.root])
        (self.root / 'escape').symlink_to('/usr/include', target_is_directory=True)
        for path in ('/usr/include', 'relative', str(self.root / 'escape/stdio.h')):
            with self.subTest(path=path), self.assertRaises(ValueError):
                gate.verify_search_paths([path], [self.root])

    def test_unknown_tool_digest_and_wrappers(self):
        p = self.root / 'wrapper'; p.write_text('#!/bin/sh\nexit 0\n'); p.chmod(0o700)
        for records in ([], [{'name': 'cc', 'path': str(p), 'sha256': gate.sha256(p)}],
                        [{'name': 'cc', 'path': str(p), 'sha256': '0' * 64}]):
            with self.assertRaises(ValueError):
                gate.verify_tools(records)

    def test_target_elf_cannot_be_selected_as_scanner_tool(self):
        import struct
        p = self.root / 'foreign-readelf'
        p.write_bytes(b'\x7fELF\x02\x01' + b'\0' * 12 + struct.pack('<H', 183))
        p.chmod(0o700)
        record = {'name': 'readelf', 'path': str(p), 'sha256': gate.sha256(p)}
        with self.assertRaises(ValueError):
            gate.verify_tools([record])

    def test_malformed_elf_and_real_host_elf_rejected(self):
        readelf = Path(shutil.which('readelf')).resolve()
        record = {'name': 'readelf', 'path': str(readelf), 'sha256': gate.sha256(readelf)}
        bad = self.root / 'bad'; bad.write_bytes(b'\x7fELF')
        with self.assertRaises(ValueError):
            gate.inspect_elf(bad, gate.sha256(bad), record, self.root, self.policy)
        host = self.root / 'host'; shutil.copyfile(Path(sys.executable).resolve(), host)
        result = gate.inspect_elf(host, gate.sha256(host), record, self.root, self.policy)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('foreign or nonexecutable ELF ABI', result['errors'])


if __name__ == '__main__':
    unittest.main()
