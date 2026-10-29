# SPDX-License-Identifier: MIT
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('controls', ROOT / 'scripts/rmxp_controls.py')
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.mapping = json.loads((ROOT / 'config/h700-controls.json').read_text())

    def test_default_matches_previous_h700_fixture(self):
        payload = C.encode(self.mapping)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),
                         'cc11f43b8f75d7de64c79ffa56a1a02528ef0483b0d811f1fc0bc77618425b6b')
        self.assertEqual(struct.unpack_from('<III', payload), (3, 1, 17))

    def test_explicit_game_override_changes_only_mapping(self):
        custom = copy.deepcopy(self.mapping)
        for binding in custom['bindings']:
            if binding['type'] == 'button' and binding['source'] == 'START':
                binding['target'] = 'F8'
        self.assertNotEqual(C.encode(custom), C.encode(self.mapping))
        self.assertEqual(len(C.encode(custom)), len(C.encode(self.mapping)))

    def test_invalid_mapping_cannot_remove_essential_controls(self):
        for change in ('duplicate', 'unknown', 'missing', 'boolean', 'extra'):
            mapping = copy.deepcopy(self.mapping)
            if change == 'duplicate':
                mapping['bindings'].append(mapping['bindings'][0])
            elif change == 'unknown':
                mapping['bindings'][0]['target'] = 'NOT_A_BUTTON'
            elif change == 'missing':
                mapping['bindings'] = [b for b in mapping['bindings'] if b['target'] != 'C']
            elif change == 'boolean':
                mapping['rgss_version'] = True
            else:
                mapping['bindings'][0]['unexpected'] = 1
            with self.assertRaises(ValueError):
                C.encode(mapping)

    def test_cli_preserves_existing_mapping(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'keybindings.mkxp1'
            command = ['python3', str(ROOT / 'scripts/rmxp_controls.py'),
                       str(ROOT / 'config/h700-controls.json'), str(output)]
            subprocess.run(command, check=True)
            before = output.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
