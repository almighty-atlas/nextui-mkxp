# SPDX-License-Identifier: MIT
"""Synthetic fixtures only: no genuine compiler, sysroot, source or device access."""
import copy
import hashlib
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


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/check_h700_engine_inputs.py'
SPEC = importlib.util.spec_from_file_location('preflight', SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def approved():
    return {'state': 'APPROVED', 'reviewer': 'synthetic-test-only',
            'evidence': 'Synthetic fixture, NOT a real approval'}


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root/'cache'
        self.cache.mkdir()
        self.manifest = {
            'schema': 1, 'scope': 'static-preparation', 'distribution': 'BLOCKED',
            'host': {'os': 'linux', 'arch': 'x86_64'},
            'target': {'os': 'linux', 'arch': 'aarch64', 'endian': 'little',
                       'triple': 'aarch64-nextui-linux-gnu',
                       'compiler_version': '8.3.0', 'kernel_headers': '4.9.170',
                       'glibc': '2.28', 'minimum_kernel': '4.9.0',
                       'interpreter': '/lib/ld-linux-aarch64.so.1'},
            'gates': {name: approved() for name in M.GATES},
            'inputs': [], 'notes': ['Synthetic fixtures only'],
        }
        for name in sorted(M.REQUIRED):
            payload = b'SYNTHETIC_NON_EXECUTABLE_INPUT_' + name.encode()
            (self.cache/name).write_bytes(payload)
            role = M.REQUIRED_ROLES[name]
            self.manifest['inputs'].append({
                'id': name, 'role': role, 'platform': M.PLATFORMS[role],
                'source': {'kind': 'git', 'revision': 'a'*40,
                           'url': 'https://example.invalid/synthetic/'+'a'*40,
                           'evidence': 'synthetic metadata only'},
                'cache_path': name, 'format': 'blob',
                'sha256': hashlib.sha256(payload).hexdigest(),
                'license': {'expression': 'MIT', 'evidence': 'synthetic test grant',
                            'obligations': 'synthetic notice, no upstream material'},
                'approval': approved(), 'blockers': [],
            })

    def result(self):
        return M.check(self.manifest, self.cache)

    def blocked(self, code):
        result = self.result()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn(code, [i['code'] for i in result['blockers']])
        self.assertFalse(result['build_authorized'])
        return result

    def item(self):
        return self.manifest['inputs'][0]

    def archive(self, name='source/file.c', kind=tarfile.REGTYPE, link='', mode=0o644):
        item = self.item()
        path = self.cache/item['cache_path']
        with tarfile.open(path, 'w') as archive:
            member = tarfile.TarInfo(name)
            member.type, member.linkname, member.mode = kind, link, mode
            member.size = 4 if kind == tarfile.REGTYPE else 0
            archive.addfile(member, io.BytesIO(b'test') if member.size else None)
        item['format'] = 'tar'
        item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()

    def cli(self, data=None):
        path = self.root/'manifest.json'
        path.write_text(json.dumps(self.manifest) if data is None else data)
        return subprocess.run([sys.executable, '-I', '-B', str(SCRIPT),
                               '--manifest', str(path), '--cache', str(self.cache)],
                              capture_output=True, text=True, timeout=10)

    def test_positive_synthetic_inputs_do_not_grant_build_or_release(self):
        result = self.result()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['checked_inputs'], len(M.REQUIRED))
        self.assertFalse(result['build_authorized'])
        self.assertEqual(result['distribution'], 'BLOCKED')

    def test_positive_synthetic_tar_and_no_extraction(self):
        self.archive()
        before = sorted(str(p) for p in self.cache.rglob('*'))
        self.assertEqual(self.result()['status'], 'PASS')
        self.assertEqual(before, sorted(str(p) for p in self.cache.rglob('*')))

    def test_changed_hash(self):
        (self.cache/self.item()['cache_path']).write_bytes(b'mutated')
        self.blocked('HASH_MISMATCH')

    def test_hash_precedes_archive_parsing(self):
        self.item()['format'] = 'tar'
        self.item()['sha256'] = '0'*64
        self.blocked('HASH_MISMATCH')

    def test_missing_archive(self):
        (self.cache/self.item()['cache_path']).unlink()
        self.blocked('UNREADABLE_OR_INVALID_INPUT')

    def test_unsafe_cache_paths(self):
        for name in ('../secret', '/etc/passwd', 'a/../b', './gcc', 'a//b',
                     'a\\b', 'C:/secret', 'gcc\n', ''):
            with self.subTest(path=name):
                self.item()['cache_path'] = name
                self.blocked('UNSAFE_PATH')

    def test_file_symlink_escape(self):
        path = self.cache/self.item()['cache_path']
        path.unlink()
        outside = self.root/'private'
        outside.write_bytes(b'PRIVATE_CONTENT_MUST_NOT_APPEAR')
        path.symlink_to(outside)
        result = self.blocked('UNREADABLE_OR_INVALID_INPUT')
        self.assertNotIn('PRIVATE_CONTENT', json.dumps(result))

    def test_directory_symlink_escape(self):
        (self.cache/'escape').symlink_to(self.root, target_is_directory=True)
        self.item()['cache_path'] = 'escape/secret'
        self.blocked('UNREADABLE_OR_INVALID_INPUT')

    def test_symlink_cache_root_refused(self):
        alias = self.root/'alias'
        alias.symlink_to(self.cache, target_is_directory=True)
        self.cache = alias
        self.blocked('UNREADABLE_OR_INVALID_INPUT')

    def test_fifo_refused_without_hang(self):
        import os
        path = self.cache/self.item()['cache_path']
        path.unlink()
        os.mkfifo(path)
        self.blocked('NOT_REGULAR_OR_TOO_LARGE')

    def test_tar_traversal(self):
        for name in ('../escape', '/absolute', 'a/../../escape', 'C:/drive', 'a\\b'):
            with self.subTest(path=name):
                self.archive(name)
                self.blocked('UNSAFE_PATH')

    def test_tar_links_and_special_members(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind):
                self.archive('source/link', kind, '../../outside')
                self.blocked('ARCHIVE_LINK_OR_SPECIAL')

    def test_tar_privileged_mode(self):
        self.archive(mode=0o4755)
        self.blocked('ARCHIVE_PRIVILEGED_MODE')

    def test_malformed_tar(self):
        self.item()['format'] = 'tar'
        self.blocked('UNREADABLE_OR_INVALID_INPUT')

    def test_missing_license_fields_and_unknown_terms(self):
        original = copy.deepcopy(self.item()['license'])
        for field in original:
            self.item()['license'] = {k: v for k, v in original.items() if k != field}
            self.blocked('SCHEMA')
        for value in (None, '', 'UNKNOWN', 'NOASSERTION', 'TBD'):
            self.item()['license'] = dict(original, expression=value)
            self.blocked('LICENSE_REQUIRED')

    def test_role_platform_mix(self):
        self.item()['role'] = 'target-runtime'
        self.item()['platform'] = 'host'
        self.blocked('HOST_TARGET_MIX')

    def test_host_elf_cannot_be_target_runtime(self):
        item = copy.deepcopy(self.item())
        item['id'] = 'extra-target'
        item['cache_path'] = 'extra-target'
        self.manifest['inputs'].append(item)
        item['role'], item['platform'] = 'target-runtime', 'target'
        payload = b'\x7fELF\x02\x01' + bytes(12) + struct.pack('<H', 62)
        (self.cache/item['cache_path']).write_bytes(payload)
        item['sha256'] = hashlib.sha256(payload).hexdigest()
        self.blocked('HOST_TARGET_MIX')

    def test_target_elf_cannot_be_host_tool(self):
        item = copy.deepcopy(self.item())
        item['id'] = 'extra-host'
        item['cache_path'] = 'extra-host'
        self.manifest['inputs'].append(item)
        item['role'], item['platform'] = 'host-tool', 'host'
        payload = b'\x7fELF\x02\x01' + bytes(12) + struct.pack('<H', 183)
        (self.cache/item['cache_path']).write_bytes(payload)
        item['sha256'] = hashlib.sha256(payload).hexdigest()
        self.blocked('HOST_TARGET_MIX')

    def test_wrong_target_baselines(self):
        original = copy.deepcopy(self.manifest['target'])
        for key, value in (('arch', 'armhf'), ('triple', 'x86_64-linux-gnu'),
                           ('minimum_kernel', '4.19.0'),
                           ('glibc', '2.31'), ('interpreter', '/host/ld.so')):
            with self.subTest(field=key):
                self.manifest['target'] = dict(original, **{key: value})
                self.blocked('TARGET_BASELINE')

    def test_open_prerequisite_gates(self):
        for gate in sorted(M.GATES):
            with self.subTest(gate=gate):
                self.manifest['gates'][gate] = dict(approved(), state='BLOCKED')
                self.blocked('APPROVAL_REQUIRED')
                self.manifest['gates'][gate] = approved()

    def test_input_grant_reviewer_and_evidence_required(self):
        original = approved()
        for key, value in (('state', 'BLOCKED'), ('reviewer', None), ('evidence', '')):
            self.item()['approval'] = dict(original, **{key: value})
            self.blocked('APPROVAL_REQUIRED')

    def test_input_blockers_and_null_hash_refused(self):
        self.item()['blockers'] = ['unresolved']
        self.blocked('INPUT_BLOCKED')
        self.item()['blockers'] = []
        self.item()['sha256'] = None
        self.blocked('HASH_REQUIRED')

    def test_moving_git_ref_refused(self):
        self.item()['source']['revision'] = 'main'
        self.blocked('UNPINNED_SOURCE')

    def test_missing_duplicate_and_unknown_fields(self):
        self.manifest['inputs'].append(copy.deepcopy(self.item()))
        self.blocked('INPUTS_REQUIRED')
        self.manifest['inputs'].pop()
        self.manifest['typo'] = True
        self.blocked('SCHEMA')

    def test_cannot_remove_required_sources_or_gates(self):
        original = copy.deepcopy(self.manifest)
        self.manifest['inputs'] = self.manifest['inputs'][1:]
        self.blocked('INPUTS_REQUIRED')
        self.manifest = original
        self.manifest['gates'].pop('issue_3')
        self.blocked('GATES_REQUIRED')

    def test_no_release_state_or_scope_escalation(self):
        self.manifest['distribution'] = 'APPROVED'
        self.blocked('SCOPE_OR_RELEASE_STOP')
        self.manifest['distribution'] = 'BLOCKED'
        self.manifest['scope'] = 'engine-build'
        self.blocked('SCOPE_OR_RELEASE_STOP')

    def test_cli_deterministic_json_and_exit_codes(self):
        first, second = self.cli(), self.cli()
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, '')
        self.item()['sha256'] = '0'*64
        failed = self.cli()
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stdout)['status'], 'BLOCKED')
        self.assertNotIn(str(self.root), failed.stdout)

    def test_cli_malformed_and_duplicate_json(self):
        for data in ('{', '{"schema":1,"schema":1}', '[]', 'null'):
            result = self.cli(data)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'BLOCKED')
            self.assertEqual(result.stderr, '')

    def test_repository_manifest_stays_blocked_and_preserves_stops(self):
        manifest = json.loads((ROOT/'build/h700-engine/inputs.json').read_text())
        result = M.check(manifest, self.cache)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(result['build_authorized'])
        self.assertEqual(result['distribution'], 'BLOCKED')
        self.assertEqual(result['checked_inputs'], 0)
        self.assertEqual({i['gate'] for i in result['blockers'] if 'gate' in i}, M.GATES)
        ids = {i['id']: i for i in manifest['inputs']}
        self.assertIsNone(ids['mkxp-z']['sha256'])
        self.assertIsNone(ids['sdl']['sha256'])
        self.assertIn('tiny02', json.dumps(manifest))

    def test_no_network_process_or_extraction_apis_in_validator(self):
        import ast
        tree = ast.parse(SCRIPT.read_text())
        imports = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
        self.assertFalse(imports & {'socket', 'urllib', 'subprocess', 'http', 'ctypes'})
        calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)}
        self.assertFalse(calls & {'extract', 'extractall', 'system', 'popen', 'execv'})

    def test_archive_duplicate_and_size_limit(self):
        item = self.item()
        path = self.cache/item['cache_path']
        with tarfile.open(path, 'w') as archive:
            for _ in range(2):
                archive.addfile(tarfile.TarInfo('same'))
        item['format'] = 'tar'
        item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.blocked('ARCHIVE_DUPLICATE')
        from unittest.mock import patch
        self.archive()
        with patch.object(M, 'MAX_MEMBERS', 0):
            self.blocked('ARCHIVE_LIMIT')

    def test_document_local_links_and_fences(self):
        import re
        path = ROOT/'docs/H700_ENGINE_PREFLIGHT.md'
        text = path.read_text()
        self.assertEqual(len(re.findall(r'^```', text, re.M)) % 2, 0)
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if '://' not in target and not target.startswith('#'):
                self.assertTrue((path.parent/target.split('#')[0]).exists(), target)


if __name__ == '__main__':
    unittest.main()
