# SPDX-License-Identifier: MIT
"""Roadmap consistency checks, not proof of gameplay or hardware execution."""
import json
from pathlib import Path
import re
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


if __name__ == '__main__':
    unittest.main()
