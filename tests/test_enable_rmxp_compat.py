# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import enable_rmxp_compat as E

GAME_ID = 'a' * 64


class EnableCompat(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sd = Path(self.temp.name)
        self.state = self.sd / E.STATE_ROOT / GAME_ID
        (self.state / 'game').mkdir(parents=True)
        self.write_config([])

    def write_config(self, preload):
        (self.state / 'mkxp.json').write_text(json.dumps({'rgssVersion': 1, 'preloadScript': preload}))

    def config(self):
        return json.loads((self.state / 'mkxp.json').read_text())

    def test_pinned_shim_matches_repository_file(self):
        self.assertEqual(E.P.digest(E.SHIM), E.SHIM_SHA256)

    def test_copies_shim_into_game_state_and_sets_single_preload(self):
        result = E.enable(self.sd, GAME_ID)
        copied = self.state / 'compat/essentials_win32_compat.rb'
        self.assertEqual(copied.read_bytes(), E.SHIM.read_bytes())
        expected = '/mnt/SDCARD/' + copied.relative_to(self.sd).as_posix()
        self.assertEqual(self.config()['preloadScript'], [expected])
        self.assertEqual(result['h700_result'], 'NOT_TESTED')
        self.assertFalse((self.state / 'mkxp.json.tmp').exists())

    def test_refuses_existing_preload_and_second_run(self):
        self.write_config(['/mnt/SDCARD/Emus/h700/RMXP.pak/rgss/pause_menu.rb'])
        with self.assertRaisesRegex(ValueError, 'Existing preload'):
            E.enable(self.sd, GAME_ID)
        self.assertFalse((self.state / 'compat').exists())
        self.write_config([])
        E.enable(self.sd, GAME_ID)
        before = (self.state / 'mkxp.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'known earlier version'):
            E.enable(self.sd, GAME_ID)
        self.assertEqual((self.state / 'mkxp.json').read_bytes(), before)

    def test_upgrades_only_a_known_earlier_shim_in_place(self):
        E.enable(self.sd, GAME_ID)
        before = (self.state / 'mkxp.json').read_bytes()
        shim = self.state / 'compat/essentials_win32_compat.rb'
        shim.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'known earlier version'):
            E.enable(self.sd, GAME_ID)
        self.assertEqual(shim.read_bytes(), b'tampered')
        old = E.P.digest(shim)
        original = E.PREVIOUS_SHA256
        E.PREVIOUS_SHA256 = {old}
        self.addCleanup(setattr, E, 'PREVIOUS_SHA256', original)
        self.assertEqual(E.enable(self.sd, GAME_ID)['status'], 'COMPAT_UPGRADED')
        self.assertEqual(shim.read_bytes(), E.SHIM.read_bytes())
        self.assertEqual((self.state / 'mkxp.json').read_bytes(), before)
        self.assertEqual(sorted(p.name for p in shim.parent.iterdir()), [shim.name])

    def test_rejects_invalid_ids_unregistered_games_and_rgss_mismatch(self):
        for game_id in ('../x', 'A' * 64, 'a' * 63):
            with self.assertRaises(ValueError):
                E.enable(self.sd, game_id)
        with self.assertRaisesRegex(ValueError, 'not registered'):
            E.enable(self.sd, 'b' * 64)
        (self.state / 'mkxp.json').write_text(json.dumps({'rgssVersion': 3, 'preloadScript': []}))
        with self.assertRaisesRegex(ValueError, 'RGSS1'):
            E.enable(self.sd, GAME_ID)

    def test_symlinked_state_refused(self):
        other = self.sd / 'elsewhere'
        other.mkdir()
        link_root = self.sd / E.STATE_ROOT / ('c' * 64)
        link_root.symlink_to(other)
        (other / 'mkxp.json').write_text(json.dumps({'rgssVersion': 1, 'preloadScript': []}))
        with self.assertRaises(ValueError):
            E.enable(self.sd, 'c' * 64)
        self.assertFalse((other / 'compat').exists())


if __name__ == '__main__':
    unittest.main()
