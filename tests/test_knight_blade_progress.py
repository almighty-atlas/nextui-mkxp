# SPDX-License-Identifier: MIT
"""Roadmap consistency checks, not proof of gameplay or hardware execution."""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KnightBladeProgress(unittest.TestCase):
    def test_weights_evidence_and_displayed_percentage(self):
        data = json.loads((ROOT / 'build/h700-engine/knight-blade-progress.json').read_text())
        milestones = data['milestones']
        self.assertEqual(sum(m['weight'] for m in milestones), 100)
        self.assertEqual(len({m['id'] for m in milestones}), len(milestones))
        for m in milestones:
            self.assertIs(type(m['done']), bool)
            self.assertIs(type(m['weight']), int)
            self.assertGreater(m['weight'], 0)
            if m['done']:
                self.assertTrue(m['evidence'])
                self.assertTrue((ROOT / m['evidence']).is_file())
        percent = sum(m['weight'] for m in milestones if m['done'])
        for file in ('README.md', 'docs/ROADMAP.md', 'docs/KNIGHT_BLADE_ROADMAP.md'):
            text = (ROOT / file).read_text()
            self.assertRegex(text, r'Knight Blade[^\n]*' + str(percent) + r'%|Current progress: ' + str(percent) + r'%')

    def test_reserve_and_build_scope(self):
        data = json.loads((ROOT / 'build/h700-engine/knight-blade-progress.json').read_text())
        reserve = data['reserve']
        self.assertEqual(reserve['hard_gib'], 5)
        self.assertEqual(reserve['stop_gib'], reserve['hard_gib'] + 1)
        self.assertEqual(reserve['fresh_setup_minimum_gib'], reserve['hard_gib'] + 2)
        build = json.loads((ROOT / 'build/h700-engine/engine-build-evidence.json').read_text())
        self.assertEqual(build['level'], 'verified-on-host')
        self.assertEqual(build['device_execution'], 'NOT_TESTED')
        self.assertEqual(build['distribution'], 'BLOCKED')
        self.assertRegex(build['artifact']['sha256'], r'^[a-f0-9]{64}$')

    def test_static_abi_evidence_does_not_claim_engine_execution(self):
        evidence = json.loads((ROOT / 'build/h700-engine/engine-abi-evidence.json').read_text())
        self.assertEqual(evidence['status'], 'STATIC_ABI_CANDIDATES_PASS')
        self.assertEqual(evidence['unresolved_strong_imports'], 0)
        self.assertEqual(len(evidence['provider_sha256']), evidence['objects'] - 1)
        self.assertEqual(evidence['engine_start'], 'NOT_TESTED')
        self.assertEqual(evidence['loader_test']['status'], 'BLOCKED')
        self.assertFalse(evidence['loader_test']['engine_main_executed'])
        for item in evidence['copy_relocations']:
            self.assertEqual(item['bytes'], 8)
            self.assertEqual(item['provider'], 'libc.so.6')

    def test_loader_script_refuses_non_device_staging_path(self):
        script = ROOT / 'scripts/h700_engine_loader.sh'
        subprocess.run(['sh', '-n', str(script)], check=True, timeout=5)
        result = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), 'INVALID_STAGING_DIRECTORY')


if __name__ == '__main__':
    unittest.main()
