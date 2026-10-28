# SPDX-License-Identifier: MIT
"""Synthetic ELF metadata/negative fixtures, not ARM binaries or hardware tests."""
import importlib.util
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import struct


SPEC = importlib.util.spec_from_file_location(
    'runtime_abi', Path(__file__).resolve().parents[1] / 'scripts/h700_runtime_abi.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


TEXT = '''
  GNU_STACK      0x0 0x0 0x0 0x0 0x0 RW 0x10
  [Requesting program interpreter: /lib/ld-linux-aarch64.so.1]
    OS: Linux, ABI: 4.9.0
 0x1 (NEEDED) Shared library: [libc.so.6]
 0xe (SONAME) Library soname: [example.so]
 0x1d (RUNPATH) Library runpath: [$ORIGIN]
Symbol table '.dynsym' contains 6 entries:
  1: 0000000000000000     0 FUNC GLOBAL DEFAULT UND memcpy@GLIBC_2.17 (2)
  2: 0000000000000000     0 NOTYPE WEAK DEFAULT UND weak_optional
  3: 0000000000000030     4 FUNC GLOBAL DEFAULT 12 public@@V1
  4: 0000000000000040     4 FUNC GLOBAL DEFAULT 12 old@V0
  5: 0000000000000050     4 FUNC GLOBAL HIDDEN 12 invisible
Version symbols section '.gnu.version' contains 6 entries:
Version needs section '.gnu.version_r' contains 1 entry:
  0x0000: Version: 1 File: libc.so.6 Cnt: 1
  0x0010: Name: GLIBC_2.17 Flags: none Version: 2
Version definition section '.gnu.version_d' contains 1 entry:
  0x0000: Rev: 1 Flags: none Index: 2 Cnt: 1 Name: V1
'''


def obj(needed=(), needs=None, exports=(), imports=(), definitions=()):
    return dict(needed=list(needed), needs=needs or {}, exports=list(exports),
                imports=list(imports), definitions=list(definitions))


def symbol(name='memcpy', version='GLIBC_2.17', default=True, weak=False):
    return dict(name=name, version=version, default=default, weak=weak)


class RuntimeABI(unittest.TestCase):
    def test_readelf_parse(self):
        f = M.parse(TEXT)
        self.assertEqual(f['needed'], ['libc.so.6'])
        self.assertEqual(f['soname'], 'example.so')
        self.assertEqual(f['runpath'], ['$ORIGIN'])
        self.assertTrue(f['stack_rw'])
        self.assertEqual(f['needs'], {'libc.so.6': ['GLIBC_2.17']})
        self.assertEqual(f['definitions'], ['V1'])
        self.assertEqual(len(f['imports']), 2)
        self.assertEqual([x['name'] for x in f['exports']], ['public', 'old'])
        self.assertTrue(f['exports'][0]['default'])
        self.assertFalse(f['exports'][1]['default'])

    def test_program_and_extension_policy(self):
        f = M.parse(TEXT)
        self.assertEqual(M.new_policy(f, 'program'), [])
        self.assertIn('INTERPRETER', M.new_policy(f, 'extension'))
        f['interpreter'] = []
        self.assertEqual(M.new_policy(f, 'extension'), [])

    def test_wrong_interpreter(self):
        f = M.parse(TEXT.replace('/lib/ld-linux-aarch64.so.1', '/tmp/loader'))
        self.assertIn('INTERPRETER', M.new_policy(f, 'program'))

    def test_kernel_floor(self):
        f = M.parse(TEXT.replace('ABI: 4.9.0', 'ABI: 4.19.0'))
        self.assertIn('KERNEL_ABOVE_4_9_170', M.new_policy(f, 'program'))
        f['kernel_notes'] = []
        self.assertIn('PROGRAM_KERNEL_BASELINE_UNKNOWN', M.new_policy(f, 'program'))

    def test_needed_path_and_exec_masquerading_as_shared(self):
        f = M.parse(TEXT)
        f['needed'] = ['/tmp/foreign.so']
        f['kind'] = 2
        self.assertIn('NEEDED_NOT_SONAME', M.new_policy(f, 'shared'))
        self.assertIn('SHARED_OBJECT_TYPE', M.new_policy(f, 'shared'))

    def test_absolute_and_empty_paths(self):
        for value in ('/usr/lib', '', '$ORIGIN/../../host', '$ORIGIN:/tmp/lib'):
            with self.subTest(value=value):
                f = M.parse(TEXT.replace('[$ORIGIN]', '[' + value + ']'))
                self.assertIn('UNREVIEWED_RPATH_RUNPATH', M.new_policy(f, 'program'))
        f = M.parse(TEXT.replace('(RUNPATH)', '(RPATH)'))
        self.assertIn('UNREVIEWED_RPATH_RUNPATH', M.new_policy(f, 'program'))

    def test_stack_and_textrel(self):
        for text in (TEXT.replace(' RW ', ' RWE '), TEXT + '\n (TEXTREL) 0x0',
                     TEXT + '\n (FLAGS) TEXTREL'):
            self.assertIn('STACK_OR_TEXTREL', M.new_policy(M.parse(text), 'program'))

    def test_copy_requires_separate_audit(self):
        f = M.parse(TEXT + '\n 00000 00000 R_AARCH64_COPY 00000 data + 0')
        self.assertIn('COPY_RELOCATION_REQUIRES_SIZE_AUDIT', M.new_policy(f, 'program'))

    def test_origin_rpath_requires_explicit_program_policy(self):
        f = M.parse(TEXT.replace('(RUNPATH)', '(RPATH)'))
        self.assertIn('UNREVIEWED_RPATH_RUNPATH', M.new_policy(f, 'program'))
        self.assertNotIn('UNREVIEWED_RPATH_RUNPATH',
                         M.new_policy(f, 'program', {'rpath': 'origin-only'}))
        for value in ('', '/job/lib', '$ORIGIN:/job/lib', '$ORIGIN/../lib'):
            bad = M.parse(TEXT.replace('(RUNPATH)', '(RPATH)').replace('[$ORIGIN]', '[' + value + ']'))
            self.assertIn('UNREVIEWED_RPATH_RUNPATH',
                          M.new_policy(bad, 'program', {'rpath': 'origin-only'}))
        with self.assertRaisesRegex(ValueError, 'INVALID_RPATH_POLICY'):
            M.new_policy(f, 'shared', {'rpath': 'origin-only'})
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_OBJECT_POLICY'):
            M.new_policy(f, 'program', {'allow_everything': True})

    def copy_fixture(self):
        app = M.parse(TEXT + '\n 1000 00000 R_AARCH64_COPY 1000 stdout@GLIBC_2.17 + 0\n'
                      '  6: 0000000000001000 8 OBJECT GLOBAL DEFAULT 28 stdout@GLIBC_2.17 (2)\n')
        libc = M.parse('  1: 0000000000002000 8 OBJECT GLOBAL DEFAULT 28 stdout@@GLIBC_2.17\n')
        libc['sha256'] = 'a' * 64
        return {'app': app, 'libc': libc}, {'libc.so.6': 'libc'}, ['app', 'libc'], {
            'stdout@GLIBC_2.17': {'provider': 'libc.so.6', 'size': 8}}

    def test_copy_object_size_version_address(self):
        objects, providers, scope, approval = self.copy_fixture()
        report = M.copy_audit('app', objects, providers, scope, approval)
        self.assertEqual(report[0]['bytes'], 8)
        self.assertEqual(report[0]['provider_sha256'], 'a' * 64)
        self.assertTrue(objects['app']['copy_relocations'])

    def test_copy_wrong_sizes_fail(self):
        for owner, size in (('app', 4), ('libc', 16)):
            objects, providers, scope, approval = self.copy_fixture()
            objects[owner]['exports'][-1]['size'] = size
            with self.assertRaisesRegex(ValueError, 'COPY_SIZE_MISMATCH'):
                M.copy_audit('app', objects, providers, scope, approval)

    def test_copy_missing_or_extra_approval_fails(self):
        objects, providers, scope, approval = self.copy_fixture()
        for bad in ({}, {**approval, 'extra': {'provider': 'libc.so.6', 'size': 8}}):
            with self.assertRaisesRegex(ValueError, 'COPY_ALLOWLIST_MISMATCH'):
                M.copy_audit('app', objects, providers, scope, bad)

    def test_copy_wrong_type_weak_address_or_version_fails(self):
        for key, value, code in (('kind', 'FUNC', 'COPY_NOT_STRONG_OBJECT'),
                                 ('weak', True, 'COPY_NOT_STRONG_OBJECT'),
                                 ('value', 0, 'COPY_ADDRESS_MISMATCH'),
                                 ('version', 'OTHER', 'COPY_DEFINITION_AMBIGUOUS_OR_MISSING')):
            objects, providers, scope, approval = self.copy_fixture()
            objects['app']['exports'][-1][key] = value
            with self.assertRaisesRegex(ValueError, code):
                M.copy_audit('app', objects, providers, scope, approval)

    def test_copy_unreachable_or_ambiguous_provider_fails(self):
        objects, providers, scope, approval = self.copy_fixture()
        with self.assertRaisesRegex(ValueError, 'COPY_PROVIDER_NOT_REACHABLE'):
            M.copy_audit('app', objects, providers, ['app'], approval)
        objects['other'] = copy.deepcopy(objects['libc'])
        with self.assertRaisesRegex(ValueError, 'COPY_DEFINITION_AMBIGUOUS_OR_MISSING'):
            M.copy_audit('app', objects, providers, scope + ['other'], approval)

    def test_copy_needs_named_version_provider(self):
        objects, providers, scope, approval = self.copy_fixture()
        objects['app']['needs'] = {}
        with self.assertRaisesRegex(ValueError, 'COPY_VERSION_PROVIDER'):
            M.copy_audit('app', objects, providers, scope, approval)

    def test_unknown_copy_relocation_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'UNPARSED_COPY_RELOCATION'):
            M.parse(' 1000 00000 R_ARM_COPY 1000 stdout + 0')

    def test_audit_integration_only_clears_copy_gate_after_size_check(self):
        objects, _, _, approval = self.copy_fixture()
        objects['app']['rpath'], objects['app']['runpath'] = ['$ORIGIN'], []
        objects['libc']['definitions'] = ['GLIBC_2.17']
        objects['libc']['exports'].append(symbol())
        objects['libc']['soname'] = 'libc.so.6'
        objects['loader'] = M.parse(' 0xe (SONAME) Library soname: [ld-linux-aarch64.so.1]')
        for name, facts in objects.items():
            facts['sha256'] = 'a' * 64
        with tempfile.TemporaryDirectory() as tmp:
            tool = Path(tmp) / 'readelf-fixture'
            tool.write_bytes(b'\x7fELF\x02\x01\x01' + bytes(11) + struct.pack('<H', 62) + bytes(44))
            plan = {'schema': 1, 'readelf': {'path': str(tool), 'sha256': 'b' * 64}, 'objects': [
                {'id': name, 'role': 'program' if name == 'app' else 'stock',
                 'file': {'path': '/' + name}, 'provides': [] if name == 'app' else [facts['soname']]}
                for name, facts in objects.items()]}
            plan['objects'][0]['policy'] = {'rpath': 'origin-only', 'copy_relocations': approval}
            with patch.object(M, 'checked', side_effect=lambda r: Path(r['path'])), \
                    patch.object(M, 'inspect', side_effect=lambda p, _: objects[p.name]):
                result = M.audit(plan)
                self.assertEqual(result['status'], 'STATIC_ABI_CANDIDATES_PASS')
                self.assertEqual(result['objects']['app']['issues'], [])
                objects['libc']['exports'][0]['size'] = 16
                with self.assertRaisesRegex(ValueError, 'COPY_SIZE_MISMATCH'):
                    M.audit(plan)

    def test_version_floor_is_numeric(self):
        for version in ('GLIBC_2.29', 'GLIBC_2.100', 'GLIBC_3.0'):
            f = M.parse(TEXT.replace('GLIBC_2.17', version))
            self.assertIn('GLIBC_ABOVE_2_28:' + version, M.new_policy(f, 'program'))
        for version in ('GLIBC_2.9', 'GLIBC_2.28'):
            self.assertEqual(M.new_policy(M.parse(TEXT.replace('GLIBC_2.17', version)),
                                          'program'), [])

    def test_private_imports(self):
        f = M.parse(TEXT.replace('GLIBC_2.17', 'GLIBC_PRIVATE'))
        self.assertIn('DIRECT_GLIBC_PRIVATE', M.new_policy(f, 'program'))

    def graph(self):
        return {'app': obj(['libc.so.6'], {'libc.so.6': ['GLIBC_2.17']},
                           imports=[symbol()]),
                'libc': obj(exports=[symbol()], definitions=['GLIBC_2.17'])}

    def test_positive_graph(self):
        result = M.graph_check(['app'], self.graph(), {'libc.so.6': 'libc'})
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['strong_imports'], 1)

    def test_missing_needed(self):
        self.assertIn('NEEDED_MISSING:libc.so.6',
                      M.graph_check(['app'], self.graph(), {})['issues'])

    def test_missing_version(self):
        graph = self.graph()
        graph['libc']['definitions'] = []
        self.assertIn('VERSION_MISSING:libc.so.6:GLIBC_2.17', M.graph_check(
            ['app'], graph, {'libc.so.6': 'libc'})['issues'])

    def test_missing_symbol_despite_version_definition(self):
        graph = self.graph()
        graph['libc']['exports'] = [symbol(version='GLIBC_2.18')]
        self.assertTrue(any(x.startswith('SYMBOL_MISSING:') for x in M.graph_check(
            ['app'], graph, {'libc.so.6': 'libc'})['issues']))

    def test_unreachable_provider_cannot_mask_missing_symbol(self):
        graph = self.graph()
        graph['libc']['exports'] = []
        graph['unrelated'] = obj(exports=[symbol()])
        self.assertTrue(M.graph_check(['app'], graph, {'libc.so.6': 'libc'})['issues'])

    def test_weak_unresolved_reported_not_failed(self):
        graph = self.graph()
        graph['app']['imports'].append(symbol(name='weak', version=None, weak=True))
        result = M.graph_check(['app'], graph, {'libc.so.6': 'libc'})
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['unresolved_weak'], ['app:weak@'])

    def test_merged_glibc_stubs(self):
        graph = self.graph()
        graph['app']['needed'].append('libpthread.so.0')
        graph['app']['needs']['libpthread.so.0'] = ['GLIBC_2.17']
        graph['stub'] = obj(definitions=['GLIBC_2.17'])
        result = M.graph_check(['app'], graph,
                               {'libc.so.6': 'libc', 'libpthread.so.0': 'stub'})
        self.assertEqual(result['issues'], [])

    def test_transitive_missing_needed_and_cycles(self):
        graph = self.graph()
        graph['libc']['needed'] = ['libc.so.6', 'missing.so']
        result = M.graph_check(['app'], graph, {'libc.so.6': 'libc'})
        self.assertEqual(result['issues'], ['NEEDED_MISSING:missing.so'])

    def test_unversioned_import_requires_default_export(self):
        graph = self.graph()
        graph['app']['imports'] = [symbol(version=None)]
        graph['libc']['exports'][0]['default'] = False
        self.assertTrue(M.graph_check(['app'], graph, {'libc.so.6': 'libc'})['issues'])

    def test_embedding_host_supplies_exports(self):
        graph = self.graph()
        graph['host'] = obj(exports=[symbol(name='rb_new', version=None)])
        graph['app']['imports'].append(symbol(name='rb_new', version=None))
        self.assertTrue(M.graph_check(['app'], graph, {'libc.so.6': 'libc'})['issues'])
        self.assertEqual(M.graph_check(['host', 'app'], graph,
                                      {'libc.so.6': 'libc'})['issues'], [])

    def test_changed_or_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input'
            path.write_bytes(b'original')
            record = {'path': str(path), 'sha256': M.digest(path)}
            self.assertEqual(M.checked(record), path)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'HASH_MISMATCH'):
                M.checked(record)
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'MISSING_ABSOLUTE_FILE'):
                M.checked(record)

    def test_malformed_version_and_soname_rejected(self):
        with self.assertRaisesRegex(ValueError, 'VERSION_WITHOUT_PROVIDER'):
            M.parse("Version needs section 'x':\n 0x0010: Name: GLIBC_2.17")
        with self.assertRaisesRegex(ValueError, 'MULTIPLE_SONAME'):
            M.parse(TEXT + '\n (SONAME) Library soname: [duplicate]')

    def test_stapsdt_note_names_are_not_versions(self):
        text = TEXT.split('Version definition section')[0]
        f = M.parse(text + '\nDisplaying notes found in: .note.stapsdt\n'
                    '  Name: pthread_create\n  0x0010: Name: memory_malloc_retry\n')
        self.assertEqual(f['needs'], {'libc.so.6': ['GLIBC_2.17']})

    def test_relocatable_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = b'\x7fELF\x02\x01\x01' + bytes(9) + struct.pack('<HH', 1, 183) + bytes(44)
            (root / 'synthetic.o').write_bytes(h)
            self.assertEqual(M.relocatables(root, Path('/not-invoked'))['objects'], 1)
            (root / 'synthetic.o').write_bytes(h[:18] + struct.pack('<H', 62) + h[20:])
            with self.assertRaisesRegex(ValueError, 'NOT_AARCH64_REL'):
                M.relocatables(root, Path('/not-invoked'))

    def test_archive_member_architecture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'synthetic.a').write_bytes(b'not an archive; readelf mocked')
            with patch.object(M.subprocess, 'run') as run:
                run.return_value.returncode = 0
                run.return_value.stderr = ''
                run.return_value.stdout = '  Machine: AArch64\n  Class: ELF64\n  Type: REL (Relocatable file)\n'
                self.assertEqual(M.relocatables(root, Path('/mock'))['archives']['synthetic.a']['members'], 1)
                run.return_value.stdout = run.return_value.stdout.replace('AArch64', 'Intel 80386')
                with self.assertRaisesRegex(ValueError, 'NON_AARCH64_ARCHIVE_MEMBER'):
                    M.relocatables(root, Path('/mock'))


if __name__ == '__main__':
    unittest.main()
