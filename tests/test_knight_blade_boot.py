# SPDX-License-Identifier: MIT
"""Offline guards for the private Knight Blade boot stage; no game data or engine."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/hardware/knight-blade-boot'
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    import mkxp_keybindings as K
    SPEC = importlib.util.spec_from_file_location('engine_stage', ROOT / 'scripts/prepare_h700_engine_smoke.py')
    P = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(P)
finally:
    sys.path.remove(str(ROOT / 'scripts'))


class Keybindings(unittest.TestCase):
    def test_reviewed_mapping_encodes_mkxp_format_3(self):
        mapping = json.loads((FIXTURE / 'keybindings.json').read_text())
        data = K.encode(mapping)
        fmt, rgss, count = struct.unpack_from('<III', data)
        self.assertEqual((fmt, rgss, count), (3, 1, len(mapping['bindings'])))
        self.assertEqual(len(data), 12 + 16 * count)
        records = {struct.unpack_from('<IIII', data, 12 + 16 * i) for i in range(count)}
        # Physical A arrives as SDL B and must confirm; SDL A cancels; Start opens menu.
        self.assertIn((2, K.BUTTONS['B'], 0, K.TARGETS['C']), records)
        self.assertIn((2, K.BUTTONS['A'], 0, K.TARGETS['B']), records)
        self.assertIn((2, K.BUTTONS['START'], 0, K.TARGETS['B']), records)
        self.assertIn((3, K.AXES['LEFTY'], 1, K.TARGETS['Down']), records)

    def test_rejects_invalid_or_duplicate_bindings(self):
        base = {'format': 3, 'rgss_version': 1}
        cases = [
            ([{'type': 'button', 'source': 'A', 'target': 'Start'}], 'TARGET'),
            ([{'type': 'button', 'source': 'PADDLE1', 'target': 'C'}], 'BUTTON'),
            ([{'type': 'axis', 'source': 'LEFTX', 'direction': 'up', 'target': 'Up'}], 'AXIS'),
            ([{'type': 'button', 'source': 'A', 'target': 'C'}] * 2, 'DUPLICATE_SOURCE'),
            ([], 'RECORD_COUNT'),
        ]
        for bindings, error in cases:
            with self.assertRaisesRegex(ValueError, error):
                K.encode(dict(base, bindings=bindings))
        with self.assertRaisesRegex(ValueError, 'FORMAT_VERSION'):
            K.encode({'format': 2, 'rgss_version': 1, 'bindings': []})


class BootStage(unittest.TestCase):
    def test_config_paths_are_consistent_and_private(self):
        config = json.loads((FIXTURE / 'mkxp.json').read_text())
        stage = re.search(r'^stage=(\S+)$', (FIXTURE / 'launch.sh').read_text(), re.M).group(1)
        run = (FIXTURE / 'run.sh').read_text()
        private = re.search(r'^private=(\S+)$', run, re.M).group(1)
        self.assertTrue(config['pathCache'])
        self.assertFalse(config['allowSymlinks'])
        self.assertNotIn('customScript', config)
        self.assertTrue(config['gameFolder'].startswith(private + '/games/'))
        self.assertTrue(all(p.startswith(private + '/rtp/') for p in config['RTP']))
        self.assertTrue(config['midiSoundFont'].startswith(private + '/soundfonts/'))
        self.assertTrue(all(p.startswith(stage + '/stdlib') for p in config['rubyLoadpath']))
        self.assertFalse(private.startswith('/mnt/SDCARD/.system'))
        self.assertIn('GAME_INPUTS.SHA256SUMS', run)
        self.assertIn('/usr/bin/timeout -k 5 1800', run)
        self.assertIn('pidof nextui.elf', run)

    def test_shell_syntax_and_host_refusal(self):
        for name in ('run.sh', 'launch.sh'):
            subprocess.run(['sh', '-n', str(FIXTURE / name)], check=True, timeout=5)
        result = subprocess.run(['sh', str(FIXTURE / 'run.sh')], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), 'INVALID_STAGING_DIRECTORY')

    def test_package_contains_generated_bindings_and_no_game_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root, prefix = Path(temp) / 'repo', Path(temp) / 'prefix'
            shutil.copytree(FIXTURE, root / 'tests/hardware/knight-blade-boot')
            (root / 'build/h700-engine').mkdir(parents=True)
            (prefix / 'stdlib').mkdir(parents=True)
            (prefix / 'mkxp-z.aarch64').write_bytes(b'synthetic non-executable fixture')
            (prefix / 'LICENSE.txt').write_text('Synthetic notice')
            (prefix / 'stdlib/a.rb').write_text('# synthetic source')
            evidence = {'status': 'STATIC_ABI_CANDIDATES_PASS',
                        'loader_test': {'status': 'ENGINE_LOADER_PASS'},
                        'engine_sha256': P.digest(prefix / 'mkxp-z.aarch64')}
            (root / 'build/h700-engine/engine-abi-evidence.json').write_text(json.dumps(evidence))
            output = Path(temp) / 'payload'
            with patch.object(P, 'ROOT', root), patch.object(P.shutil, 'disk_usage') as disk:
                disk.return_value.free = 6 * 1024**3
                P.prepare(prefix, output, 'knight-blade-boot')
            receipt = json.loads(output.with_suffix('.receipt.json').read_text())
            self.assertEqual(receipt['fixture'], 'knight-blade-boot')
            names = set(receipt['files'])
            self.assertTrue({'engine', 'mkxp.json', 'run.sh', 'keybindings.mkxp1'} <= names)
            self.assertFalse(any(n.lower().endswith(('.rxdata', '.sf2', '.mid', '.ogg', '.png'))
                                 for n in names))


if __name__ == '__main__':
    unittest.main()
