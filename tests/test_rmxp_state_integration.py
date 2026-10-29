# SPDX-License-Identifier: MIT
"""Optional integration against the unmerged #8 candidate; runs automatically once merged."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PAK_SOURCE = Path(os.environ.get('RMXP_PAK_SOURCE', ROOT / 'scripts/rmxp_pak.py'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(PAK_SOURCE.is_file(), 'PR #40 candidate not present; set RMXP_PAK_SOURCE')
class PakStateIntegration(unittest.TestCase):
    def test_restart_and_runtime_upgrade_preserve_independent_saves(self):
        pak_tools = load('pak_tools_integration', PAK_SOURCE)
        state_tools = load('state_tools_integration', ROOT / 'scripts/rmxp_state.py')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sd = root / 'sd'
            sd.mkdir()
            markers = []
            for name in ('Game A', 'Game B'):
                game = sd / 'Games' / name
                for part in ('Data', 'Graphics', 'Audio'):
                    (game / part).mkdir(parents=True)
                (game / 'Game.ini').write_text('[Game]\n')
                (game / 'Save1.rxdata').write_text('original\n')
                markers.append(pak_tools.register(sd, game, name, str(sd)))
            states = [sd / '.userdata/h700/nextui-mkxp' / m.read_text().strip() for m in markers]
            runtime = root / 'runtime'
            (runtime / 'stdlib').mkdir(parents=True)
            (runtime / 'stdlib/example.rb').write_text('# synthetic')
            (runtime / 'LICENSE.txt').write_text('synthetic test only')
            env = dict(os.environ, IS_NEXT='yes', PLATFORM='h700', SDCARD_PATH=str(sd),
                       USERDATA_PATH=str(sd / '.userdata/h700'))
            state_tools.snapshot(states[0], root / 'before')
            for version in ('v1', 'v2'):
                (runtime / 'engine').write_text('#!/bin/sh\nprintf "' + version + '\\n" >> game/Save1.rxdata\n')
                with patch.object(pak_tools, 'ENGINE_SHA256', pak_tools.digest(runtime / 'engine')):
                    pak = pak_tools.install(sd, runtime)
                for _ in range(2):
                    result = subprocess.run(['sh', str(pak / 'launch.sh'), str(markers[0])], env=env,
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(state_tools.diagnostics(states[0])['outcome'], 'returned_zero')
                self.assertEqual((states[1] / 'game/Save1.rxdata').read_text(), 'original\n')
                self.assertEqual((sd / 'Games/Game A/Save1.rxdata').read_text(), 'original\n')
                # Simulate owner swapping the runtime only; retain the old synthetic Pak.
                pak.rename(pak.with_name('runtime-' + version + '.disabled'))
            self.assertEqual((states[0] / 'game/Save1.rxdata').read_text(), 'original\nv1\nv1\nv2\nv2\n')
            state_tools.snapshot(states[0], root / 'after')
            self.assertNotEqual(state_tools.verify(root / 'before')['files'],
                                state_tools.verify(root / 'after')['files'])
