# SPDX-License-Identifier: MIT
"""Synthetic metadata/policy tests; never a C++ build, ELF link or ARM run."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/h700_cxx_abi.py'
SPEC = importlib.util.spec_from_file_location('cxx_gate', SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def header_fixture(machine=183, kind=2):
    # NONEXECUTABLE 64-byte header fixture, not a real DSO or cross-link input.
    return b'\x7fELF\x02\x01\x01'+bytes(9)+struct.pack('<HH', kind, machine)+bytes(44)


def readelf_fixture():
    return '''[Requesting program interpreter: /lib/ld-linux-aarch64.so.1]
  (NEEDED) Shared library: [libstdc++.so.6]
  (NEEDED) Shared library: [libgcc_s.so.1]
  (NEEDED) Shared library: [libc.so.6]
  GNU_STACK 0x0 0x0 0x0 0x0 0x0 RW 0x10
  OS: Linux, ABI: 4.9.0
Version needs section '.gnu.version_r' contains 3 entries:
  File: libstdc++.so.6 Cnt: 2
  Name: GLIBCXX_3.4.21 Flags: none
  Name: CXXABI_1.3 Flags: none
  File: libc.so.6 Cnt: 1
  Name: GLIBC_2.17 Flags: none
  File: libgcc_s.so.1 Cnt: 1
  Name: GCC_3.0 Flags: none
Version definition section '.gnu.version_d' contains 1 entry:
  Name: GLIBC_99.99
'''


class CxxGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.compiler = self.root/'compiler'
        self.sysroot = self.root/'sysroot'
        self.old = self.compiler/'old-sdk'
        self.headers = self.compiler/'include/c++/8.3.0'
        self.runtime = self.compiler/'lib/gcc/8.3.0'
        self.cxxlibs = self.compiler/'target/lib64'
        for path in (self.old, self.headers, self.runtime, self.cxxlibs,
                     self.sysroot/'lib64', self.sysroot/'usr/lib64', self.sysroot/'usr/include'):
            path.mkdir(parents=True, exist_ok=True)
        self.startups = []
        for name in ('crt1.o', 'crti.o', 'crtn.o', 'crtbegin.o', 'crtend.o'):
            folder = self.runtime if name.startswith(('crtbegin', 'crtend')) else self.sysroot/'usr/lib64'
            path = folder/name
            path.write_bytes(header_fixture(kind=1))
            self.startups.append(str(path))
        self.paths = {'includes': [str(self.headers), str(self.sysroot/'usr/include')],
                      'libraries': [str(self.cxxlibs), str(self.runtime), str(self.sysroot/'lib64')],
                      'startups': self.startups}
        self.roots = {'compiler_headers': [self.headers], 'sysroot': self.sysroot,
                      'compiler_runtime': self.runtime, 'cxx_library_dir': self.cxxlibs,
                      'old_sdk': self.old}

    def test_original_cpp_surface_is_present_not_compiled_by_this_test(self):
        text = M.SOURCE.read_text()
        for name in ('std::make_unique', 'std::string', 'std::runtime_error',
                     'catch', '~Lifetime', 'destroyed != 2'):
            self.assertIn(name, text)
        self.assertNotIn('SDL', text)

    def test_search_positive_is_only_metadata_audit(self):
        result = M.search_audit(**self.paths, **self.roots)
        self.assertFalse(result['cross_link_performed'])

    def test_old_sdk_library_include_and_startup_are_refused(self):
        for field in ('includes', 'libraries', 'startups'):
            values = copy.deepcopy(self.paths)
            values[field].append(str(self.old))
            with self.subTest(field=field), self.assertRaises(M.Blocked):
                M.search_audit(**values, **self.roots)

    def test_host_include_and_relative_path_are_refused(self):
        for value in ('relative', str(self.root)):
            values = dict(self.paths, includes=[value])
            with self.assertRaises(M.Blocked):
                M.search_audit(**values, **self.roots)

    def test_symlink_search_escape_refused(self):
        escape = self.headers/'escape'
        escape.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(M.Blocked):
            M.search_audit(**dict(self.paths, includes=[str(escape)]), **self.roots)

    def test_missing_or_wrong_startup_set_refused(self):
        for startups in ([], self.startups[:-1], self.startups + self.startups[:1]):
            with self.assertRaises(M.Blocked):
                M.search_audit(**dict(self.paths, startups=startups), **self.roots)

    def test_exact_20_gib_floor(self):
        for free, passes in ((M.RESERVE, True), (M.RESERVE-1, False)):
            with patch.object(M.shutil, 'disk_usage') as usage:
                usage.return_value.free = free
                if passes:
                    M.reserve(self.root)
                else:
                    with self.assertRaisesRegex(M.Blocked, '20_GIB'):
                        M.reserve(self.root)

    def test_native_compiler_absence_is_blocked_not_skip_or_pass(self):
        with patch.object(M.shutil, 'which', return_value=None), \
                patch.object(M.platform, 'system', return_value='Linux'), \
                patch.object(M.platform, 'machine', return_value='x86_64'), \
                patch.object(M.subprocess, 'run') as run:
            with self.assertRaisesRegex(M.Blocked, 'NATIVE_CXX_COMPILER_UNAVAILABLE'):
                M.native(self.root/'unused')
            run.assert_not_called()
            self.assertFalse((self.root/'unused').exists())

    def test_native_mode_rejects_target_compiler_and_scripts_before_execution(self):
        compiler = self.root/'not-a-native-compiler'
        for payload in (header_fixture(), b'#!/bin/sh\nexit 0\n'):
            compiler.write_bytes(payload)
            with patch.object(M.subprocess, 'run') as run:
                with self.assertRaises(M.Blocked):
                    M.native(self.root/'unused', compiler)
                run.assert_not_called()

    def test_native_output_must_be_host_elf_before_any_execution(self):
        compiler = self.root/'native-tool-header-only'
        compiler.write_bytes(header_fixture(machine=62))
        work = self.root/'private-native'
        def fake_compile(*args, **kwargs):
            (work/'probe-native').write_bytes(header_fixture(machine=183))
            self.assertNotIn('LD_PRELOAD', kwargs['env'])
            self.assertNotIn('CPLUS_INCLUDE_PATH', kwargs['env'])
            return subprocess.CompletedProcess(args, 0, b'', b'')
        with patch.object(M.subprocess, 'run', side_effect=fake_compile) as run, \
                patch.object(M, 'reserve'):
            with self.assertRaisesRegex(M.Blocked, 'ELF_MACHINE_OR_TYPE'):
                M.native(work, compiler)
            self.assertEqual(run.call_count, 1)  # Mock compile only; no fake ARM run.

    def test_elf_version_definitions_do_not_become_needs(self):
        facts = M.parse_readelf(readelf_fixture())
        self.assertNotIn('GLIBC_99.99', str(facts['needs']))
        self.assertIn('GLIBC_99.99', facts['definitions'])
        self.assertEqual(facts['needs']['libstdc++.so.6'], ['CXXABI_1.3', 'GLIBCXX_3.4.21'])

    def test_synthetic_elf_policy_requires_exact_provider_definitions(self):
        facts = M.parse_readelf(readelf_fixture())
        result = M.elf_policy(facts, facts['needs'])
        self.assertEqual(result['status'], 'ELF_POLICY_ONLY')
        definitions = copy.deepcopy(facts['needs'])
        definitions['libstdc++.so.6'].remove('CXXABI_1.3')
        with self.assertRaisesRegex(M.Blocked, 'UNRESOLVED_VERSION_PROVIDER'):
            M.elf_policy(facts, definitions)

    def test_elf_policy_rejects_bad_kernel_loader_rpath_stack_or_needed(self):
        for old, new in (('ABI: 4.9.0', 'ABI: 4.19.0'),
                         ('/lib/ld-linux-aarch64.so.1', '/host/ld.so'),
                         (' RW 0x10', ' RWE 0x10'),
                         ('[libc.so.6]', '[libforeign.so]')):
            facts = M.parse_readelf(readelf_fixture().replace(old, new))
            with self.subTest(change=new), self.assertRaises(M.Blocked):
                M.elf_policy(facts, facts['needs'])
        for extra in ('(RPATH) [/old]', '(RUNPATH) [/old]', '(TEXTREL) 0x1'):
            facts = M.parse_readelf(readelf_fixture()+'\n'+extra)
            with self.assertRaises(M.Blocked):
                M.elf_policy(facts, facts['needs'])

    def test_elf_policy_rejects_private_too_new_and_wrong_version_provider(self):
        for old, new in (('GLIBC_2.17', 'GLIBC_PRIVATE'), ('GLIBC_2.17', 'GLIBC_2.29'),
                         ('GLIBC_2.17', 'GLIBCXX_3.4.21')):
            facts = M.parse_readelf(readelf_fixture().replace(old, new))
            with self.subTest(version=new), self.assertRaises(M.Blocked):
                M.elf_policy(facts, facts['needs'])

    def test_actual_readelf_is_never_invoked_on_bad_host_tool_or_target_header(self):
        tool, binary = self.root/'tool-header-only', self.root/'bad-target'
        tool.write_bytes(header_fixture(machine=62))
        binary.write_bytes(header_fixture(machine=62))
        with patch.object(M.subprocess, 'run') as run:
            with self.assertRaises(M.Blocked):
                M.inspect(binary, tool, M.sha(tool))
            run.assert_not_called()
        with self.assertRaisesRegex(M.Blocked, 'READELF_HASH'):
            M.inspect(binary, tool, '0'*64)

    def test_synthetic_readelf_invocation_is_host_only_and_facts_not_pass(self):
        tool, binary = self.root/'tool-header-only', self.root/'target-header-only'
        tool.write_bytes(header_fixture(machine=62))
        binary.write_bytes(header_fixture())
        result = subprocess.CompletedProcess([], 0, readelf_fixture(), '')
        with patch.object(M.subprocess, 'run', return_value=result) as run:
            facts = M.inspect(binary, tool, M.sha(tool))
        self.assertEqual(facts['status'], 'ELF_FACTS_ONLY')
        self.assertEqual(facts['policy'], 'NOT_EVALUATED')
        self.assertEqual(run.call_args.args[0][0], str(tool))
        self.assertEqual(run.call_args.kwargs['env'], M.ENV)

    def test_link_map_known_files_only_no_old_sdk(self):
        path = Path(self.startups[0])
        result = M.audit_link_map('LOAD '+str(path)+'\n', {str(path): M.sha(path)}, self.old)
        self.assertEqual(result['load_records'], 1)
        with self.assertRaisesRegex(M.Blocked, 'UNKNOWN_MAP_INPUT'):
            M.audit_link_map('LOAD '+str(path), {}, self.old)
        with self.assertRaisesRegex(M.Blocked, 'LOCAL_INPUT_HASH'):
            M.audit_link_map('LOAD '+str(path), {str(path): '0'*64}, self.old)
        old = self.old/'libc.so'
        old.write_text('synthetic old SDK script')
        with self.assertRaisesRegex(M.Blocked, 'OLD_SDK_INPUT'):
            M.audit_link_map('LOAD '+str(old), {str(old): M.sha(old)}, self.old)

    def test_owner_provider_facts_not_promoted_to_local_verification(self):
        evidence = json.loads((ROOT/'build/h700-engine/cxx-provider-evidence.json').read_text())
        self.assertFalse(evidence['local_provider_bytes_checked'])
        self.assertEqual(evidence['cross_build_status'], 'CROSS_BUILD_BLOCKED')
        self.assertEqual(evidence['distribution'], 'BLOCKED')
        self.assertEqual({p['file']: p['sha256'] for p in evidence['providers']}, M.PROVIDERS)

    def test_template_cannot_approve_cross_link(self):
        plan = json.loads((ROOT/'build/h700-engine/cxx-cross-plan.example.json').read_text())
        with self.assertRaises(M.Blocked):
            M.cross_audit(plan)

    def test_cross_cli_reports_missing_real_receipts_not_mock_success(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), 'cross-status'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        data = json.loads(result.stdout)
        self.assertEqual(data['status'], 'CROSS_BUILD_BLOCKED')
        self.assertEqual(data['arm_execution'], 'NEVER')
        self.assertNotIn(str(self.root), result.stdout)

    def test_malformed_cross_plan_is_blocked_without_traceback(self):
        plan = self.root/'bad-plan.json'
        for data in ('[]', 'null', '{'):
            plan.write_text(data)
            result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT),
                                     'cross-audit', '--plan', str(plan)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, '')
            self.assertEqual(json.loads(result.stdout)['status'], 'CROSS_BUILD_BLOCKED')

    def test_cross_audit_synthetic_receipts_only_not_real_build(self):
        def record(path):
            return {'path': str(path), 'sha256': M.sha(path)}
        archive = self.root/'synthetic-archive'
        archive.write_bytes(b'NOT_A_REAL_COMPILER_ARCHIVE')
        lock = self.root/'synthetic-lock.json'
        lock.write_text(json.dumps({'compiler': {'sha256': M.sha(archive)}}))
        sysroot = self.root/'synthetic-sysroot-receipt.json'
        sysroot.write_text(json.dumps({'source_lock_sha256': M.sha(lock),
                                      'sysroot_tree_sha256': M.tree_digest(self.sysroot),
                                      'target_execution': 'NEVER', 'distribution': 'BLOCKED'}))
        sdl = self.root/'synthetic-sdl-receipt.json'
        sdl.write_text(json.dumps({'status': 'SDL_ONLY_HOST_LINKED',
                                  'sysroot_tree': M.tree_digest(self.sysroot)}))
        providers = {}
        for name in M.PROVIDERS:
            path = self.cxxlibs/name
            path.write_bytes(header_fixture(kind=3))
            providers[name] = record(path)
        plan = {'schema': 1, 'scope': 'private-cxx14-calibration',
                'source_sha256': M.sha(M.SOURCE), 'compiler_root': str(self.compiler),
                'reviewed_compiler_tree_sha256': M.tree_digest(self.compiler),
                'sysroot': str(self.sysroot), 'old_sdk': str(self.old),
                'compiler_headers': [str(self.headers)], 'compiler_runtime': str(self.runtime),
                'cxx_library_dir': str(self.cxxlibs), **self.paths,
                'startup_records': {p: M.sha(p) for p in self.startups},
                'compiler_archive': record(archive), 'providers': providers,
                'receipts': {'input_lock': record(lock), 'sysroot': record(sysroot), 'sdl': record(sdl)}}
        # Substitute synthetic trust anchors only inside this explicitly fake fixture.
        with patch.object(M, 'COMPILER_ARCHIVE_HASH', M.sha(archive)), \
                patch.object(M, 'PROVIDERS', {n: r['sha256'] for n, r in providers.items()}), \
                patch.object(M, 'reserve'):
            result = M.cross_audit(plan)
            self.assertFalse(result['cross_link_performed'])
            self.assertEqual(result['complete_link_input_closure'], 'NOT_CHECKED')
            original_receipt = json.loads(sysroot.read_text())
            for field, code in (('source_lock_sha256', 'LOCK_RECEIPT_MISMATCH'),
                                ('sysroot_tree_sha256', 'SYSROOT_TREE')):
                sysroot.write_text(json.dumps(dict(original_receipt, **{field: '0'*64})))
                plan['receipts']['sysroot'] = record(sysroot)
                with self.subTest(field=field), self.assertRaisesRegex(M.Blocked, code):
                    M.cross_audit(plan)
            sysroot.write_text(json.dumps(original_receipt))
            plan['receipts']['sysroot'] = record(sysroot)
            original_sdl = sdl.read_text()
            sdl.write_text(json.dumps({'status': 'SDL_ONLY_HOST_LINKED', 'sysroot_tree': '0'*64}))
            plan['receipts']['sdl'] = record(sdl)
            with self.assertRaisesRegex(M.Blocked, 'SDL_RECEIPT_MISMATCH'):
                M.cross_audit(plan)
            sdl.write_text(original_sdl)
            plan['receipts']['sdl'] = record(sdl)
            sysroot.write_text('{}')
            with self.assertRaisesRegex(M.Blocked, 'LOCAL_INPUT_HASH'):
                M.cross_audit(plan)


if __name__ == '__main__':
    unittest.main()
