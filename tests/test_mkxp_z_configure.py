# SPDX-License-Identifier: MIT
"""Offline argv/text tests. No Docker, Meson, compiler or ARM execution."""
import argparse
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SPEC = importlib.util.spec_from_file_location('configure', SCRIPTS / 'mkxp_z_configure.py')
M = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(M)
finally:
    sys.path.remove(str(SCRIPTS))

PROFILE = {'meson_options': {'sdl_system': 'enabled', 'use_miniffi': False}}


class Configure(unittest.TestCase):
    def args(self, native='/private/native'):
        return argparse.Namespace(native=Path(native), toolchain=Path('/private/gcc'),
                                  sysroot=Path('/private/sysroot'))

    def test_cross_file_uses_pinned_target_tools_and_private_pkgconfig(self):
        text = M.cross_file()
        self.assertIn("cpu_family = 'aarch64'", text)
        self.assertIn('aarch64-nextui-linux-gnu-gcc', text)
        self.assertIn("'--sysroot=" + M.SYSROOT + "'", text)
        self.assertIn("pkg_config_libdir = ['/job/sdl-prefix/lib/pkgconfig']", text)
        self.assertIn("ruby = '/work/prefix/bin/ruby'", text)
        self.assertNotIn('/usr/lib/pkgconfig', text)

    def test_no_pkgconfig_sysroot_prefix(self):
        self.assertNotIn('sys_root', M.cross_file().replace('No sys_root', ''))

    def test_local_patch_appended_before_sentinel_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, sub = Path(tmp) / 'repo', Path(tmp) / 'subprojects'
            (root / 'patches').mkdir(parents=True)
            (sub / 'packagefiles').mkdir(parents=True)
            patch_file = root / 'patches/fix.patch'
            patch_file.write_text('# fixture\n')
            (sub / 'z.wrap').write_text('[wrap-file]\ndiff_files =\n    up.patch,\n'
                                        '    end-of-diff-files.patch\n')
            profile = {'local_patches': {'z': [{'file': 'patches/fix.patch',
                                                'sha256': M.sha(patch_file)}]}}
            with patch.object(M, 'ROOT', root):
                applied = M.add_local_patches(sub, profile)
                self.assertEqual(list(applied), ['patches/fix.patch'])
                self.assertIn('    up.patch,\n    nextui-fix.patch,\n    end-of-diff-files.patch\n',
                              (sub / 'z.wrap').read_text())
                self.assertTrue((sub / 'packagefiles/nextui-fix.patch').is_file())
                profile['local_patches']['z'][0]['sha256'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'LOCAL_PATCH_HASH'):
                    M.add_local_patches(sub, profile)

    def test_repository_local_patch_matches_profile(self):
        import json
        profile = json.loads((M.ROOT / 'build/h700-engine/mkxp-z-profile.json').read_text())
        for patches in profile['local_patches'].values():
            for item in patches:
                self.assertEqual(M.sha(M.ROOT / item['file']), item['sha256'])

    def test_sdl_pc_has_no_rpath(self):
        pc = M.sdl_pc()
        self.assertNotIn('rpath', pc)
        self.assertIn('-lSDL2', pc)

    def test_setup_command_offline_and_options(self):
        cmd = M.setup_command(PROFILE)
        self.assertIn('--wrap-mode=nodownload', cmd)
        self.assertIn('-Dsdl_system=enabled', cmd)
        self.assertIn('-Duse_miniffi=false', cmd)

    def test_container_limits(self):
        cmd = M.docker_command(self.args(), Path('/private/job'), 'test', M.setup_command(PROFILE))
        for option in ('--pull=never', '--network=none', '--read-only', '--cpus=2',
                       '--memory=4g', '--memory-swap=4g', '--cap-drop=ALL'):
            self.assertIn(option, cmd)
        self.assertIn('build_alias=' + M.BUILD_ALIAS, cmd)
        self.assertNotIn('--privileged', cmd)
        self.assertIn('type=bind,src=/private/native,dst=/work,readonly', cmd)
        self.assertEqual(cmd[cmd.index(M.IMAGE) + 1], 'setup')

    def test_mount_injection_rejected(self):
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_MOUNT_PATH'):
            M.docker_command(self.args('/x,readonly=false'), Path('/job'), 'test', M.COMPILE_COMMAND)

    def test_locked_diffs_applied_in_order_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, files = Path(tmp) / 'src', Path(tmp) / 'pf'
            root.mkdir()
            files.mkdir()
            (root / 'a.txt').write_text('one\n')
            (files / '1.patch').write_text('--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-one\n+two\n')
            (files / '2.patch').write_text('--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-two\n+three\n')
            diffs = {n: M.sha(files / n) for n in ('1.patch', '2.patch')}
            M.apply_diffs(root, files, diffs)
            self.assertEqual((root / 'a.txt').read_text(), 'three\n')
            with self.assertRaisesRegex(ValueError, 'DIFF_FILE_HASH'):
                M.apply_diffs(root, files, {'1.patch': '0' * 64})
            with self.assertRaisesRegex(ValueError, 'DIFF_APPLY_FAILED'):
                M.apply_diffs(root, files, {'1.patch': diffs['1.patch']})

    def test_reserve_guard(self):
        with patch.object(M.shutil, 'disk_usage') as disk, patch.object(M, 'tree_size', return_value=0):
            disk.return_value.free = 6 * M.GIB - 1
            with self.assertRaisesRegex(ValueError, 'FREE_SPACE_GUARD_6_GIB'):
                M.guard(Path('/unused'), M.GIB, 5)
            disk.return_value.free = 6 * M.GIB
            M.guard(Path('/unused'), M.GIB, 5)

    def test_reserve_below_approval_rejected(self):
        args = argparse.Namespace(reserve_gib=4)
        with patch.object(M.os, 'getuid', return_value=1000):
            with self.assertRaisesRegex(ValueError, 'RESERVE_BELOW_OWNER_APPROVAL'):
                M.resolve_tools(args)

    def test_compile_command_in_container(self):
        cmd = M.docker_command(self.args(), Path('/private/job'), 'test', M.COMPILE_COMMAND)
        self.assertEqual(cmd[cmd.index(M.IMAGE) - 1], '--entrypoint=meson')
        self.assertEqual(cmd[cmd.index(M.IMAGE) + 1:], ['compile', '-C', '/job/build', '-j', '2'])

    def test_engine_outputs_only_aarch64_elf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            elf = b'\x7fELF\x02\x01\x01' + bytes(9)
            (root / 'mkxp-z').write_bytes(elf + struct.pack('<HH', 3, 183) + bytes(44))
            (root / 'host-tool').write_bytes(elf + struct.pack('<HH', 3, 62) + bytes(44))
            (root / 'notes.txt').write_text('not an ELF')
            self.assertEqual(list(M.engine_outputs(root)), ['mkxp-z'])

    def test_exec_attempt_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'meson-logs').mkdir()
            (root / 'meson-logs/meson-log.txt').write_text('Checking compiler: yes\n')
            self.assertEqual(M.exec_attempts(root), [])
            (root / 'config.log').write_text('./conftest: cannot execute binary file\n')
            self.assertEqual(M.exec_attempts(root), ['config.log'])


if __name__ == '__main__':
    unittest.main()
