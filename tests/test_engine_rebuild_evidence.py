# SPDX-License-Identifier: MIT
"""Evidence consistency only: these tests do not rebuild or prove hardware use."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EngineRebuildEvidence(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'build/h700-engine/engine-rebuild-evidence.json').read_text())

    def test_repeated_binary_hashes_match_original_evidence(self):
        original = json.loads((ROOT / self.data['original_build_evidence']).read_text())
        self.assertEqual(self.data['artifact'], original['artifact'])
        self.assertEqual(self.data['staged_artifact_sha256'],
                         original['private_staging']['artifact_sha256'])
        self.assertTrue(self.data['build_binary_byte_identical'])
        self.assertTrue(self.data['staged_binary_byte_identical'])

    def test_driver_lock_and_profile_are_exact(self):
        for key, path in (('driver_sha256', 'scripts/mkxp_z_configure.py'),
                          ('lock_sha256', 'build/h700-engine/mkxp-z-lock.json'),
                          ('profile_sha256', 'build/h700-engine/mkxp-z-profile.json')):
            self.assertEqual(self.data[key], hashlib.sha256((ROOT / path).read_bytes()).hexdigest())

    def test_runtime_equality_does_not_hide_gemspec_or_bootstrap_gaps(self):
        self.assertTrue(self.data['pak_runtime_files']['byte_identical'])
        self.assertFalse(self.data['full_upstream_stage']['byte_identical'])
        self.assertEqual(self.data['full_upstream_stage']['different_files'], 69)
        self.assertEqual(self.data['target_execution_attempts'], [])
        self.assertEqual(self.data['level'], 'verified-on-host')
        self.assertEqual(self.data['device_execution'], 'NOT_TESTED')
        self.assertEqual(self.data['clean_room_tool_bootstrap'], 'NOT_VERIFIED')
        self.assertEqual(self.data['distribution'], 'BLOCKED')
