# SPDX-License-Identifier: MIT
"""Offline guard/argv tests. No Docker, cross compiler or ARM execution."""
import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    'ruby_batch', Path(__file__).resolve().parents[1] / 'scripts/h700_ruby_batch.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class RubyBatch(unittest.TestCase):
    def test_container_limits_and_roots(self):
        args = argparse.Namespace(native=Path('/private/native'), seed=Path('/private/seed'),
                                  toolchain=Path('/private/gcc'), sysroot=Path('/private/sysroot'),
                                  zlib=Path('/private/zlib'), reuse_encodings=False,
                                  support_only=False)
        cmd = M.command(args, Path('/private/job'), 'test-container')
        for option in ('--pull=never', '--network=none', '--read-only', '--cpus=2',
                       '--memory=4g', '--memory-swap=4g', '--cap-drop=ALL'):
            self.assertIn(option, cmd)
        self.assertNotIn('--privileged', cmd)
        self.assertEqual(cmd[-3:], [M.IMAGE, '/batch.sh', 'full'])
        args.reuse_encodings = True
        self.assertEqual(M.command(args, Path('/private/job'), 'test-container')[-1],
                         'reuse-encodings')
        self.assertIn('type=bind,src=/private/native,dst=/work,readonly', cmd)
        self.assertIn('type=bind,src=/private/job/target,dst=/target', cmd)

    def test_mount_option_injection(self):
        args = argparse.Namespace(native=Path('/private/evil,readonly=false'),
                                  toolchain=Path('/gcc'), sysroot=Path('/sysroot'), zlib=Path('/zlib'),
                                  reuse_encodings=False, support_only=False)
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_MOUNT_PATH'):
            M.command(args, Path('/job'), 'test')

    def test_space_floor_includes_headroom(self):
        with patch.object(M.shutil, 'disk_usage') as disk, patch.object(M, 'size', return_value=0):
            disk.return_value.free = 25 * M.GIB
            with self.assertRaisesRegex(ValueError, 'FREE_SPACE_GUARD'):
                M.guard(Path('/unused'))
            disk.return_value.free = 26 * M.GIB
            M.guard(Path('/unused'))

    def test_output_budget(self):
        with patch.object(M.shutil, 'disk_usage') as disk, patch.object(M, 'size', return_value=M.GIB + 1):
            disk.return_value.free = 30 * M.GIB
            with self.assertRaisesRegex(ValueError, 'PRIVATE_JOB_BUDGET'):
                M.guard(Path('/unused'))

    def test_seed_change_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'libruby.so.3.1.3'
            p.write_bytes(b'not a target ELF')
            with self.assertRaisesRegex(ValueError, 'EXISTING_ARTIFACT_CHANGED'):
                M.unchanged(Path(tmp))

    def test_archive_hash_required_before_source_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'source.tar.xz'
            p.write_bytes(b'not an archive')
            with self.assertRaisesRegex(ValueError, 'RUBY_ARCHIVE_HASH'):
                M.source_check(p, Path(tmp))

    def test_no_target_execution_attempt_in_configure(self):
        good = 'ac_cv_env_build_alias_value=x86_64-pc-linux-gnu\nconfigure:1: result: yes\n'
        M.configure_guard(good)
        with self.assertRaisesRegex(ValueError, 'TARGET_EXECUTION_ATTEMPT'):
            M.configure_guard(good + 'configure:4731: ./conftest\n')
        with self.assertRaisesRegex(ValueError, 'EXPLICIT_LIBFFI_BUILD_ALIAS_MISSING'):
            M.configure_guard('configure:1: result: yes\n')


if __name__ == '__main__':
    unittest.main()
