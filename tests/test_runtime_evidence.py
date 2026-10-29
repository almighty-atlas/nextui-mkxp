# SPDX-License-Identifier: MIT
"""Consistency checks for captured evidence. Never substitute for device execution."""
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeEvidence(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads((ROOT / 'build/h700-engine/runtime-batch-evidence.json').read_text())

    def test_captured_log_and_script_hashes(self):
        trial = self.evidence['trial']
        records = [(trial['log'], trial['log_sha256']),
                   ('tests/hardware/ruby_runtime.rb', trial['test_script_sha256']),
                   ('scripts/h700_ruby_trial.sh', trial['runner_sha256'])]
        for path, expected in records:
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)

    def test_device_identity_and_actual_markers(self):
        device, trial = self.evidence['device'], self.evidence['trial']
        self.assertEqual(device['arch'], 'aarch64')
        for key in ('baseos', 'nextui', 'nextui_revision', 'kernel'):
            self.assertTrue(device[key])
        lines = (ROOT / trial['log']).read_text().splitlines()
        self.assertEqual([line[5:] for line in lines if line.startswith('PASS ')], trial['passed'])
        self.assertEqual(lines[-1], 'RUBY_RUNTIME_BATCH_PASS')
        self.assertEqual(trial['exit_code'], 0)
        self.assertNotIn('FAIL ', '\n'.join(lines))

    def test_distribution_and_scope_not_promoted(self):
        self.assertEqual(self.evidence['distribution'], 'BLOCKED')
        self.assertEqual(self.evidence['engine_start'], 'NOT_TESTED')
        self.assertEqual(self.evidence['public_clean_room_reproducibility'], 'NOT_ESTABLISHED')
        self.assertFalse(self.evidence['trial']['firmware_libraries_bundled'])
        self.assertFalse(self.evidence['static_audit']['runtime_loader_simulation'])

    def test_hash_records(self):
        for name in ('selected_artifact_sha256', 'stock_provider_sha256_confirmed_before_and_after_trial'):
            for path, value in self.evidence[name].items():
                self.assertRegex(value, r'\A[a-f0-9]{64}\Z', path)


if __name__ == '__main__':
    unittest.main()
