# SPDX-License-Identifier: MIT
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_packed_rmxp as P
from test_fangame_audit import packed, scripts


class PackedGameCandidate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        usage = P.shutil.disk_usage(self.root)._replace(free=20 * P.GIB)
        space = patch.object(P.shutil, 'disk_usage', return_value=usage)
        space.start()
        self.addCleanup(space.stop)
        self.game = self.root / 'original'
        for folder in ('Audio', 'Graphics'):
            (self.game / folder).mkdir(parents=True)
        (self.game / 'Game.ini').write_text('[Game]\nScripts=Data\\Scripts.rxdata\n')
        self.archive = self.game / 'Game.rgssad'
        self.archive.write_bytes(packed([('Data/Scripts.rxdata', scripts(b'fixture')),
                                        ('Graphics/fixture.dat', b'synthetic image placeholder')]))
        self.expected = P.P.digest(self.archive)
        self.stage = self.root / 'stage'

    def test_only_new_copies_get_data_mount_point_and_no_overlay(self):
        (self.game / 'Graphics').rmdir()
        result = P.prepare(self.game, self.expected, self.stage, 'Private Candidate')
        self.assertEqual(result['h700_result'], 'NOT_TESTED')
        self.assertFalse((self.game / 'Data').exists())
        self.assertTrue((self.stage / 'Games/Private Candidate/Data').is_dir())
        self.assertTrue((self.stage / 'Games/Private Candidate/Graphics').is_dir())
        target = self.stage / '.userdata/h700/nextui-mkxp' / result['game_id']
        self.assertEqual(P.P.digest(target / 'game/Game.rgssad'), self.expected)
        self.assertEqual(P.json.loads((target / 'mkxp.json').read_text())['preloadScript'], [])
        self.assertFalse(result['ruby_executed'])

    def test_hash_and_repeated_stage_fail_without_original_changes(self):
        with self.assertRaises(ValueError):
            P.prepare(self.game, '0' * 64, self.stage, 'Private Candidate')
        self.assertFalse(self.stage.exists())
        P.prepare(self.game, self.expected, self.stage, 'Private Candidate')
        with self.assertRaises(ValueError):
            P.prepare(self.game, self.expected, self.stage, 'Private Candidate')
        self.assertEqual(P.P.digest(self.archive), self.expected)

    def test_unsafe_name_and_special_input_refused(self):
        with self.assertRaises(ValueError):
            P.prepare(self.game, self.expected, self.stage, '../outside')
        (self.game / 'link').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            P.prepare(self.game, self.expected, self.stage, 'Private Candidate')
        self.assertFalse(self.stage.exists())
