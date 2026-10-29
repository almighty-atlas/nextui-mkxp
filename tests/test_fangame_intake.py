# SPDX-License-Identifier: MIT
"""Source-report consistency, not proof of game contents or compatibility."""
import json
import hashlib
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

    def test_supplied_payload_evidence_does_not_promote_host_inventory_to_playability(self):
        report = json.loads((ROOT / 'build/h700-engine/fangame-host-inventory.json').read_text())
        self.assertEqual(report['level'], 'verified-on-host')
        self.assertFalse(report['game_bundle_downloaded_by_agent'])
        self.assertFalse(report['game_or_installer_executed'])
        self.assertEqual(report['device_connection'], 'SSH_TIMEOUT')
        for game in report['games']:
            self.assertRegex(game['archive_sha256'], r'^[a-f0-9]{64}$')
            self.assertGreater(game['archive_bytes'], 0)
            self.assertEqual(game['h700_result'], 'NOT_TESTED')
            self.assertEqual(game['pause_menu'], 'DISABLED_PENDING_ADAPTER')
        rocket = next(g for g in report['games'] if g['id'] == 'team-rocket-lucksack')
        self.assertEqual(rocket['cab_offset'] + rocket['cab_bytes'], rocket['wrapper_bytes'])
        self.assertEqual(rocket['cab_entries'], 1005)

    def test_extractor_tools_are_pinned_and_not_target_dependencies(self):
        report = json.loads((ROOT / 'build/h700-engine/private-extractor-tool-evidence.json').read_text())
        self.assertFalse(report['host_package_installation'])
        self.assertFalse(report['game_bundle_downloads'])
        self.assertFalse(report['tool_binary_distribution'])
        for package in report['packages']:
            self.assertRegex(package['sha256'], r'^[a-f0-9]{64}$')
            self.assertEqual(package['arch'], 'amd64')

    def test_device_staging_evidence_is_not_a_gameplay_claim(self):
        report = json.loads((ROOT / 'build/h700-engine/fangame-device-stage.json').read_text())
        self.assertEqual(report['level'], 'verified-on-H700')
        self.assertEqual(report['existing_save_checksums'], {'records': 7, 'result': 'UNCHANGED'})
        self.assertFalse(report['game_launch_by_agent'])
        self.assertFalse(report['firmware_or_service_changes'])
        for game in report['games']:
            self.assertEqual(game['checksums'], 'ALL_PASS')
            self.assertEqual(game['h700_game_result'], 'NOT_TESTED')
            self.assertEqual(game['preload_scripts'], [])
            self.assertEqual(game['game_id'], hashlib.sha256(game['source'].encode()).hexdigest())
        launch = report['first_owner_launch']
        self.assertEqual(launch['result'], 'BOTH_ABORTED_BEFORE_TITLE')
        adapter = report['compat_adapter']
        self.assertEqual(adapter['h700_game_result'], 'NOT_TESTED')
        shim = ROOT / adapter['script']
        self.assertEqual(hashlib.sha256(shim.read_bytes()).hexdigest(), adapter['sha256'])
        resume = report['sage_resume']
        self.assertEqual(resume['already_verified_files'] + resume['resent_files'],
                         report['games'][0]['manifest_files'])
