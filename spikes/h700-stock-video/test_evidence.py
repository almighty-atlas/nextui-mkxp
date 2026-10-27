# SPDX-License-Identifier: MIT
"""Offline documentation consistency, never device/ELF verification."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads((ROOT/'spikes/h700-stock-video/evidence.json').read_text())
        cls.followup = cls.evidence['hardware_followup']
        cls.report = (ROOT/'docs/H700_VIDEO_EVIDENCE.md').read_text()

    def test_historical_blocker_is_preserved_not_current_runtime(self):
        self.assertEqual(self.evidence['historical_preparation_status'], 'BUILD_BLOCKED')
        self.assertEqual(self.evidence['toolchain_probe']['gcc_version_exit'], 127)
        self.assertIsNone(self.evidence['new_target_elf'])
        self.assertIn('earlier Alpine', self.evidence['historical_fields_scope'])
        self.assertEqual(self.evidence['status'], 'LIMITED_H700_VIDEO_PASS_OWNER_OBSERVED')

    def test_exact_supplied_candidate_and_guard_facts(self):
        digest = 'd41477f3a3803ee22e778629d4b5c9a0947cd4449e1717f1e7f347226a09a5f9'
        self.assertEqual(self.followup['elf_sha256'], digest)
        self.assertIn(digest, self.report)
        self.assertEqual(self.followup['host_facts']['sdl_exports'], 21)
        self.assertEqual(self.followup['host_facts']['initial_markers'],
                         ['HOST_VERIFIED', 'SOURCE_ONLY'])
        self.assertTrue(self.followup['post_trial']['source_only_restored'])
        self.assertTrue(self.followup['post_trial']['elf_hash_rechecked_successfully'])
        self.assertFalse(self.followup['further_device_action_authorized'])
        self.assertEqual(self.followup['distribution'], 'BLOCKED')

    def test_trace_and_observation_are_separate_and_consistent(self):
        trace = self.followup['trace']
        for key in ('sdl_compiled', 'sdl_linked', 'sdl_driver', 'gl_vendor',
                    'gl_renderer', 'gl_version', 'glsl_version', 'frames', 'elapsed_ms'):
            self.assertIn(f'{key}={trace[key]}', self.report)
        self.assertEqual(trace['frames'], 297)
        self.assertEqual(trace['elapsed_ms'], 5007)
        self.assertEqual(trace['last_stage'], 'exit_owner_verification_required')
        self.assertTrue(self.followup['owner_observation']['visible_colorful_moving_triangle'])
        self.assertTrue(self.followup['owner_observation']['nextui_menu_operable'])
        self.assertIsNone(self.followup['device']['exact_firmware_version'])
        for missing in ('audio', 'mkxp-z startup', 'performance/stability'):
            self.assertIn(missing, self.followup['not_tested'])

    def test_local_document_links_and_markdown_fences(self):
        import re
        paths = ['README.md', 'docs/ARCHITECTURE.md', 'docs/ROADMAP.md',
                 'docs/TEST_PLAN.md', 'docs/COMPATIBILITY.md',
                 'docs/H700_VIDEO_EVIDENCE.md', 'docs/H700_MINIMAL_ENGINE_PLAN.md',
                 'spikes/h700-stock-video/README.md']
        for name in paths:
            path = ROOT/name
            text = path.read_text()
            with self.subTest(path=name):
                self.assertEqual(len(re.findall(r'^```', text, re.M)) % 2, 0)
                for target in re.findall(r'\]\(([^)]+)\)', text):
                    if '://' not in target and not target.startswith('#'):
                        self.assertTrue((path.parent/target.split('#')[0]).exists(), target)
        self.assertTrue((ROOT/'spikes/h700-stock-video'/
                         self.followup['evidence_document']).is_file())


if __name__ == '__main__':
    unittest.main()
