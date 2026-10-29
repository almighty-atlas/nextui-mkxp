# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import rmxp_recovery_check as R


class RecoveryCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sd = self.root / 'sd'
        self.game = self.sd / 'Games/Original'
        for directory in ('Data', 'Graphics', 'Audio'):
            (self.game / directory).mkdir(parents=True)
        (self.game / 'Game.ini').write_text('[Game]\n')
        (self.game / 'Save2.rxdata').write_bytes(b'synthetic saved progress')
        marker = R.P.register(self.sd, self.game, 'Original')
        self.state = self.sd / '.userdata/h700/nextui-mkxp' / marker.read_text().strip()
        (self.state / 'pause_menu.rb').write_text('# synthetic preload')
        (self.state / 'session.conf').write_text('/dev/input/event1\n310\n311\n')
        self.output = self.root / 'recovery'

    def test_restore_is_exact_and_playable_copy_has_new_rebased_id(self):
        before = R.S.inventory(self.state)
        result = R.prepare(self.state, self.output)
        self.assertEqual(result['hardware_load'], 'NOT_TESTED')
        self.assertEqual(R.S.inventory(self.state), before)
        restored = self.output / 'restored-sd/.userdata/h700/nextui-mkxp' / self.state.name
        self.assertEqual(R.S.inventory(restored), before)
        out = self.output / 'out-sd'
        marker = out / 'Roms/RPG Maker XP (RMXP)/Knight Blade Recovery.rmxp'
        new = out / '.userdata/h700/nextui-mkxp' / marker.read_text().strip()
        self.assertNotEqual(new.name, self.state.name)
        self.assertEqual(R.S.inventory(new / 'game'), R.S.inventory(self.state / 'game'))
        config = R.json.loads((new / 'mkxp.json').read_text())
        self.assertIn(new.name, config['gameFolder'])
        self.assertIn(new.name, config['preloadScript'][0])
        self.assertNotIn(self.state.name, str(config))
        self.assertEqual((new / 'session.conf').read_bytes(), (self.state / 'session.conf').read_bytes())

    def test_existing_output_and_original_id_cannot_be_reused(self):
        with self.assertRaisesRegex(ValueError, 'RECOVERY_ID_COLLISION'):
            R.prepare(self.state, self.output, 'Original')
        self.assertFalse(self.output.exists())
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'FRESH_WORKSPACE_REQUIRED'):
            R.prepare(self.state, self.output)

    def test_running_or_readonly_inputs_are_safe(self):
        (self.state / 'lock').mkdir()
        with self.assertRaisesRegex(ValueError, 'STATE_LOCKED'):
            R.prepare(self.state, self.output)
        self.assertFalse(self.output.exists())
        (self.state / 'lock').rmdir()
        (self.state / 'game/Save2.rxdata').chmod(0o400)
        R.prepare(self.state, self.output)
        restored = self.output / 'restored-sd/.userdata/h700/nextui-mkxp' / self.state.name
        self.assertTrue((restored / 'game/Save2.rxdata').stat().st_mode & 0o200)

    def test_unsafe_name_and_low_space_do_not_create_output(self):
        for name in ('../escape', '/outside', '.hidden'):
            with self.assertRaises(ValueError):
                R.prepare(self.state, self.output, name)
            self.assertFalse(self.output.exists())
        usage = R.shutil.disk_usage(self.root)._replace(free=1)
        with patch.object(R.shutil, 'disk_usage', return_value=usage):
            with self.assertRaisesRegex(ValueError, 'INSUFFICIENT_SPACE'):
                R.prepare(self.state, self.output)
        self.assertFalse(self.output.exists())

    def test_fresh_game_starts_without_inheriting_custom_script_paths(self):
        (self.state / 'pause_menu.rb').unlink()
        R.prepare(self.state, self.output, name="Recovery ü's", device_root='/mnt/sdcard')
        marker = self.output / "out-sd/Roms/RPG Maker XP (RMXP)/Recovery ü's.rmxp"
        new = self.output / 'out-sd/.userdata/h700/nextui-mkxp' / marker.read_text().strip()
        config = R.json.loads((new / 'mkxp.json').read_text())
        self.assertEqual(config['preloadScript'], [])
        self.assertTrue(config['gameFolder'].startswith('/mnt/sdcard/'))
