# SPDX-License-Identifier: MIT
"""Exercise real host supervisor + Pak launcher + private diagnostic exporter."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PAK = Path(os.environ.get('RMXP_PAK_SOURCE', ROOT / 'scripts/rmxp_pak.py'))
STATE = Path(os.environ.get('RMXP_STATE_SOURCE', ROOT / 'scripts/rmxp_state.py'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(PAK.is_file() and STATE.is_file(), 'PR #40/#41 candidates unavailable')
class SessionIntegration(unittest.TestCase):
    def test_actual_wait_status_reaches_bounded_pak_diagnostics(self):
        p, s = load('integration_pak', PAK), load('integration_state', STATE)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            helper = root / 'rmxp-session'
            subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                            str(ROOT / 'native/rmxp-session.c'), '-o', str(helper)], check=True)
            for number, (ending, expected, status) in enumerate((
                    ('exit 0', 'returned_zero', 0),
                    ('exit 143', 'failed', 143),
                    ('kill -TERM $$', 'signaled', 143))):
                sd = root / str(number)
                game = sd / 'Games/Test ü'
                for directory in ('Data', 'Graphics', 'Audio'):
                    (game / directory).mkdir(parents=True)
                (game / 'Game.ini').write_text('[Game]\n')
                marker = p.register(sd, game, 'Test ü', str(sd))
                runtime = root / ('runtime' + str(number))
                (runtime / 'stdlib').mkdir(parents=True)
                (runtime / 'stdlib/fixture.rb').write_text('# synthetic')
                (runtime / 'LICENSE.txt').write_text('synthetic fixture')
                (runtime / 'engine').write_text('#!/bin/sh\ni=0; while test "$i" -lt 400; do echo PRIVATE_SENTINEL; i=$((i+1)); done\n' + ending + '\n')
                with patch.object(p, 'ENGINE_SHA256', p.digest(runtime / 'engine')), \
                        patch.object(p, 'SESSION_SHA256', p.digest(helper)):
                    pak = p.install(sd, runtime, helper)
                env = dict(os.environ, IS_NEXT='yes', PLATFORM='h700', SDCARD_PATH=str(sd),
                           USERDATA_PATH=str(sd / '.userdata/h700'))
                result = subprocess.run(['sh', str(pak / 'launch.sh'), str(marker)], env=env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0 if status == 0 else 2, result.stderr)
                state = sd / '.userdata/h700/nextui-mkxp' / marker.read_text().strip()
                report = s.diagnostics(state)
                self.assertEqual(report['outcome'], expected)
                self.assertEqual(report['exit_code'], status)
                self.assertEqual(report['stop_reason'], 'natural')
                self.assertNotIn('PRIVATE_SENTINEL', str(report))
                self.assertLessEqual(len((state / 'run.log').read_text().splitlines()), 258)
                self.assertFalse((state / 'lock').exists())
