# SPDX-License-Identifier: MIT
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pak', ROOT / 'scripts/rmxp_pak.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class PakTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sd = Path(self.temp.name) / 'sd'
        self.sd.mkdir()

    def game(self, name='Knight ü $()'):
        game = self.sd / 'Games' / name
        game.mkdir(parents=True)
        (game / 'Game.ini').write_text('[Game]\nScripts=Data/Scripts.rxdata\n')
        for directory in ('Data', 'Graphics', 'Audio'):
            (game / directory).mkdir()
        (game / 'Save1.rxdata').write_text('synthetic existing save')
        return game

    def runtime(self):
        runtime = Path(self.temp.name) / 'runtime'
        (runtime / 'stdlib').mkdir(parents=True)
        (runtime / 'stdlib/test.rb').write_text('# synthetic')
        (runtime / 'LICENSE.txt').write_text('synthetic test fixture')
        (runtime / 'engine').write_text(
            '#!/bin/sh\nprintf "changed" > game/Save1.rxdata\n'
            'i=0; while test "$i" -lt 400; do echo test-output; i=$((i+1)); done\n')
        with patch.object(P, 'ENGINE_SHA256', P.digest(runtime / 'engine')):
            return P.install(self.sd, runtime)

    def launch(self, pak, marker):
        env = dict(os.environ, IS_NEXT='yes', PLATFORM='h700', SDCARD_PATH=str(self.sd),
                   USERDATA_PATH=str(self.sd / '.userdata/h700'))
        return subprocess.run(['sh', str(pak / 'launch.sh'), str(marker)], env=env,
                              text=True, capture_output=True, timeout=10)

    def test_two_games_and_literal_unicode_shell_paths(self):
        first = self.game("Knight's ü $(touch NEVER)")
        second = self.game('Other game')
        a = P.register(self.sd, first, "Knight's ü", str(self.sd))
        b = P.register(self.sd, second, 'Other', str(self.sd))
        self.assertNotEqual(a.read_text(), b.read_text())
        state = self.sd / '.userdata/h700/nextui-mkxp' / a.read_text().strip()
        config = json.loads((state / 'mkxp.json').read_text())
        self.assertEqual(config['gameFolder'], str(state / 'game'))
        pak = self.runtime()
        result = self.launch(pak, a)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((state / 'game/Save1.rxdata').read_text(), 'changed')
        self.assertEqual((first / 'Save1.rxdata').read_text(), 'synthetic existing save')
        other = state.parent / b.read_text().strip()
        self.assertEqual((other / 'game/Save1.rxdata').read_text(), 'synthetic existing save')
        self.assertFalse((state / 'lock').exists())
        self.assertEqual(len((state / 'run.log').read_text().splitlines()), 257)
        self.assertIn('RMXP_EXIT=0', (state / 'run.log').read_text())
        with self.assertRaisesRegex(ValueError, 'Already registered'):
            P.register(self.sd, first, 'new name', str(self.sd))

    def test_failures_do_not_launch(self):
        game = self.game()
        marker = P.register(self.sd, game, 'Test', str(self.sd))
        pak = self.runtime()
        (game / 'Game.ini').unlink()
        result = self.launch(pak, marker)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Game.ini missing', result.stderr)
        marker.write_text('../../bad')
        self.assertIn('Invalid game entry', self.launch(pak, marker).stderr)

    def test_runtime_tampering_and_lock(self):
        marker = P.register(self.sd, self.game(), 'Test', str(self.sd))
        pak = self.runtime()
        state = self.sd / '.userdata/h700/nextui-mkxp' / marker.read_text().strip()
        (state / 'lock').mkdir()
        self.assertIn('Game busy', self.launch(pak, marker).stderr)
        (state / 'lock').rmdir()
        (pak / 'engine').write_text('# altered')
        self.assertIn('Runtime checksum failed', self.launch(pak, marker).stderr)
        self.assertFalse((state / 'lock').exists())

    def test_input_and_destination_rejection(self):
        game = self.game()
        for name in ('../escape', '.hidden', 'bad\nname', 'ü' * 130):
            with self.assertRaises(ValueError):
                P.register(self.sd, game, name)
        (game / 'Data/link').symlink_to(game / 'Game.ini')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            P.register(self.sd, game, 'Test')
        (game / 'Data/link').unlink()
        (self.sd / '.userdata').symlink_to(self.sd / 'Games', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Destination symlink'):
            P.register(self.sd, game, 'Test')

    def test_engine_failure_preserves_exit_and_unlocks(self):
        marker = P.register(self.sd, self.game(), 'Test', str(self.sd))
        pak = self.runtime()
        (pak / 'engine').write_text('#!/bin/sh\necho synthetic-failure\nexit 17\n')
        manifest = pak / 'SHA256SUMS'
        lines = manifest.read_text().splitlines()
        manifest.write_text('\n'.join(P.digest(pak / 'engine') + '  engine'
                                     if line.endswith('  engine') else line for line in lines) + '\n')
        result = self.launch(pak, marker)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Engine failed', result.stderr)
        state = self.sd / '.userdata/h700/nextui-mkxp' / marker.read_text().strip()
        self.assertIn('RMXP_EXIT=17', (state / 'run.log').read_text())
        self.assertFalse((state / 'lock').exists())

    def test_missing_assets(self):
        game = self.game()
        (game / 'Audio').rmdir()
        with self.assertRaisesRegex(ValueError, 'Audio directory missing'):
            P.register(self.sd, game, 'Test')
        self.assertFalse((self.sd / '.userdata').exists())

    def test_kit_and_archive_validation(self):
        archive = Path(self.temp.name) / 'kit.zip'
        subprocess.run(['python3', str(ROOT / 'scripts/rmxp_pak.py'), 'kit', str(archive)], check=True)
        P.validate_archive(archive)
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(set(z.namelist()), set(P.KIT_FILES))
        with zipfile.ZipFile(archive, 'a') as z:
            z.writestr('../escape', 'bad')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            P.validate_archive(archive)

    def test_host_refusal_and_syntax(self):
        launcher = ROOT / 'pak/RMXP.pak/launch.sh'
        subprocess.run(['sh', '-n', str(launcher)], check=True)
        result = subprocess.run(['sh', str(launcher)], env={'PATH': '/usr/bin:/bin'}, capture_output=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
