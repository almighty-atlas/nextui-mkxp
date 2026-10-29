# SPDX-License-Identifier: MIT
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('state_tools', ROOT / 'scripts/rmxp_state.py')
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.card = self.root / 'card'
        self.card.mkdir()
        self.state = self.make_state('a')
        self.backup = self.root / 'backup'

    def make_state(self, letter):
        state = self.card / '.userdata/h700/nextui-mkxp' / (letter * 64)
        (state / 'game/Graphics').mkdir(parents=True)
        (state / 'game/Audio').mkdir()
        (state / 'game/Data').mkdir()
        (state / 'game/Game.ini').write_text('[Game]\nTitle=synthetic\n')
        (state / "game/Save ü '1.rxdata").write_bytes(b'synthetic save\x00')
        (state / 'source.path').write_text('Games/Synthetic\n')
        (state / 'mkxp.json').write_text('{"rgssVersion": 1}\n')
        return state

    def test_round_trip_preserves_all_data_and_empty_directories(self):
        original = S.inventory(self.state)
        self.assertEqual(S.snapshot(self.state, self.backup)['status'], 'SNAPSHOT_VERIFIED')
        manifest = S.verify(self.backup)
        self.assertEqual(manifest['game_id'], self.state.name)
        second_card = self.root / 'second-card'
        second_card.mkdir()
        S.restore(self.backup, second_card)
        restored = second_card / self.state.relative_to(self.card)
        self.assertEqual(S.inventory(restored), original)
        self.assertEqual(S.inventory(self.state), original)
        self.assertFalse((restored / 'lock').exists())
        self.assertFalse((self.state / 'lock').exists())

    def test_existing_state_and_backup_never_overwritten(self):
        S.snapshot(self.state, self.backup)
        original = S.inventory(self.state)
        with self.assertRaisesRegex(ValueError, 'EXISTING_STATE_PRESERVED'):
            S.restore(self.backup, self.card)
        with self.assertRaisesRegex(ValueError, 'FRESH_BACKUP_REQUIRED'):
            S.snapshot(self.state, self.backup)
        self.assertEqual(S.inventory(self.state), original)

    def test_games_remain_independent_across_snapshots(self):
        other = self.make_state('b')
        before = S.inventory(other)
        S.snapshot(self.state, self.backup)
        (self.state / "game/Save ü '1.rxdata").write_text('new private save')
        S.snapshot(self.state, self.root / 'backup-new')
        self.assertEqual(S.inventory(other), before)
        self.assertNotEqual(S.verify(self.backup)['files'], S.verify(self.root / 'backup-new')['files'])

    def test_read_only_game_files_restored_writable(self):
        save = self.state / "game/Save ü '1.rxdata"
        save.chmod(0o444)
        S.snapshot(self.state, self.backup)
        second_card = self.root / 'second-card'
        second_card.mkdir()
        S.restore(self.backup, second_card)
        recovered = second_card / save.relative_to(self.card)
        self.assertTrue(recovered.stat().st_mode & 0o200)
        self.assertFalse(save.stat().st_mode & 0o200)

    def test_locked_state_refuses_backup(self):
        (self.state / 'lock').mkdir()
        with self.assertRaisesRegex(ValueError, 'STATE_LOCKED'):
            S.snapshot(self.state, self.backup)
        self.assertFalse(self.backup.exists())
        self.assertTrue((self.state / 'lock').exists())

    def test_failed_copy_is_incomplete_without_data_deletion(self):
        original = S.inventory(self.state)
        with patch.object(S, 'copy_inventory', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                S.snapshot(self.state, self.backup)
        with self.assertRaisesRegex(ValueError, 'INCOMPLETE_BACKUP'):
            S.verify(self.backup)
        self.assertEqual(S.inventory(self.state), original)
        self.assertTrue(self.backup.is_dir())
        self.assertFalse((self.state / 'lock').exists())

    def test_interrupted_restore_remains_locked(self):
        S.snapshot(self.state, self.backup)
        second_card = self.root / 'second-card'
        second_card.mkdir()
        with patch.object(S, 'copy_inventory', side_effect=OSError('synthetic interruption')):
            with self.assertRaises(OSError):
                S.restore(self.backup, second_card)
        restored = second_card / self.state.relative_to(self.card)
        self.assertTrue((restored / 'lock').exists())
        S.verify(self.backup)

    def test_concurrent_source_change_does_not_finalize_backup(self):
        copy = S.copy_inventory
        def changing_copy(*args):
            copy(*args)
            (self.state / "game/Save ü '1.rxdata").write_text('concurrent write')
        with patch.object(S, 'copy_inventory', side_effect=changing_copy):
            with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED'):
                S.snapshot(self.state, self.backup)
        self.assertFalse((self.backup / 'manifest.json').exists())
        self.assertFalse((self.state / 'lock').exists())

    def test_tampered_and_extra_backup_files_rejected(self):
        S.snapshot(self.state, self.backup)
        extra = self.backup / 'payload/unlisted'
        extra.write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'BACKUP_CONTENT_MISMATCH'):
            S.verify(self.backup)
        extra.unlink()
        (self.backup / 'payload/game/Game.ini').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'BACKUP_CONTENT_MISMATCH'):
            S.verify(self.backup)

    def test_symlinks_special_files_and_nested_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'BACKUP_INSIDE_STATE'):
            S.snapshot(self.state, self.state / 'backup')
        link = self.state / 'game/link'
        link.symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, 'SPECIAL_FILE_OR_SYMLINK'):
            S.snapshot(self.state, self.backup)
        link.unlink()
        os.mkfifo(self.state / 'game/fifo')
        with self.assertRaisesRegex(ValueError, 'SPECIAL_FILE_OR_SYMLINK'):
            S.snapshot(self.state, self.backup)

    def test_manifest_traversal_and_reserved_paths_rejected(self):
        S.snapshot(self.state, self.backup)
        path = self.backup / 'manifest.json'
        original = path.read_text()
        for bad in ('../escape', '/absolute', '.', 'lock', 'recovery.pending/x'):
            manifest = json.loads(original)
            manifest['directories'].append(bad)
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'UNSAFE_MANIFEST_PATH'):
                S.verify(self.backup)

    def test_low_space_preserves_source(self):
        with patch.object(S, 'MANIFEST_LIMIT', 1):
            with self.assertRaisesRegex(ValueError, 'MANIFEST_TOO_LARGE'):
                S.snapshot(self.state, self.backup)
        self.assertFalse(self.backup.exists())
        usage = shutil.disk_usage(self.root)._replace(free=1)
        with patch.object(S.shutil, 'disk_usage', return_value=usage):
            with self.assertRaisesRegex(ValueError, 'INSUFFICIENT_FREE_SPACE'):
                S.snapshot(self.state, self.backup)
        self.assertFalse(self.backup.exists())
        self.assertFalse((self.state / 'lock').exists())

    def test_diagnostics_export_does_not_echo_private_content(self):
        private = '/home/SECRET_USER/Game Password=SECRET_TOKEN 192.0.2.50 https://secret.invalid'
        (self.state / 'run.log').write_text(private + '\nerror while loading shared libraries: SECRET.so\nRMXP_EXIT=127\n')
        report = S.diagnostics(self.state)
        encoded = json.dumps(report)
        for secret in ('SECRET', '192.0.2.50', 'secret.invalid', self.state.name):
            self.assertNotIn(secret, encoded)
        self.assertEqual(report['outcome'], 'failed')
        self.assertEqual(report['categories'], ['missing_library'])

    def test_diagnostics_outcomes_and_bounded_scan(self):
        log = self.state / 'run.log'
        for ending, outcome in (('RMXP_EXIT=0\n', 'returned_zero'),
                                ('RMXP_EXIT=139\n', 'signal_or_high_exit'),
                                ('unfinished\n', 'incomplete_or_unrecognized')):
            log.write_text(ending)
            self.assertEqual(S.diagnostics(self.state)['outcome'], outcome)
        log.write_bytes(b'x' * (S.SCAN_LIMIT + 1) + b'\nRMXP_EXIT=0\n')
        report = S.diagnostics(self.state)
        self.assertTrue(report['scan_truncated'])
        self.assertEqual(report['outcome'], 'returned_zero')
        (self.state / 'lock').mkdir()
        self.assertEqual(S.diagnostics(self.state)['outcome'], 'locked_or_running')

    def test_cli_error_has_no_private_path_or_traceback(self):
        result = subprocess.run(['python3', str(ROOT / 'scripts/rmxp_state.py'), 'verify',
                                 '--backup', str(self.root / 'PRIVATE_SECRET')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, '')
        self.assertNotIn('PRIVATE_SECRET', result.stdout)
        self.assertEqual(json.loads(result.stdout)['code'], 'INCOMPLETE_BACKUP')


if __name__ == '__main__':
    unittest.main()
