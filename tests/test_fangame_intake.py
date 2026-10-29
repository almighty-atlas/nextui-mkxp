# SPDX-License-Identifier: MIT
"""Source-report consistency, not proof of game contents or compatibility."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FangameIntake(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'build/h700-engine/fangame-intake.json').read_text())

    def test_no_downloads_or_hardware_results_are_invented(self):
        self.assertFalse(self.data['automatic_bundle_download'])
        self.assertFalse(self.data['payloads_inspected'])
        self.assertEqual({g['id'] for g in self.data['games']},
                         {'sage', 'reborn', 'team-rocket-lucksack'})
        for game in self.data['games']:
            self.assertIsNone(game['payload_sha256'])
            self.assertIsNone(game['essentials_version'])
            self.assertFalse(game['native_calls_reviewed'])
            self.assertEqual(game['h700_result'], 'NOT_TESTED')
            self.assertEqual(game['pause_menu'], 'DISABLED_PENDING_ADAPTER')
            self.assertTrue(game['blockers'])

    def test_variant_and_save_risks_are_recorded(self):
        reborn = next(g for g in self.data['games'] if g['id'] == 'reborn')
        self.assertEqual(reborn['page_claimed_version'], '19.5')
        self.assertIn('Windows 19.5', reborn['selected_input'])
        self.assertEqual(reborn['faq_save_file'], 'Game.rxdata')
        self.assertIn('4 GB', reborn['upstream_ram_requirement'])
        rocket = next(g for g in self.data['games'] if g['id'] == 'team-rocket-lucksack')
        self.assertEqual(rocket['page_access'], 'HTTP_403')
        self.assertIsNone(rocket['page_claimed_version'])

    def test_only_landing_pages_not_signed_downloads_are_persisted(self):
        text = json.dumps(self.data)
        self.assertNotIn('download2389.mediafire.com', text)
        self.assertNotIn('dkey=', text)
        for game in self.data['games']:
            self.assertTrue(game['source_page'].startswith('https://'))
