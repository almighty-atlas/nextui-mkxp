# SPDX-License-Identifier: MIT
"""Allowlist/copy tests with synthetic text files, never target binary fixtures."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SPEC = importlib.util.spec_from_file_location('prepare_trial', SCRIPTS / 'prepare_h700_ruby_trial.py')
M = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(M)
finally:
    sys.path.remove(str(SCRIPTS))


class TrialPreparation(unittest.TestCase):
    def test_only_ruby_source_is_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'src', Path(tmp) / 'out'
            source.mkdir()
            (source / 'sub').mkdir()
            (source / 'sub/a.rb').write_text('# original fixture')
            (source / 'foreign.so').write_bytes(b'not an ELF; must never be copied')
            (source / 'game.rxdata').write_bytes(b'not a game; rejection fixture')
            M.pure_ruby(source, target)
            self.assertEqual([str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()],
                             ['sub/a.rb'])

    def test_source_links_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'src', Path(tmp) / 'out'
            source.mkdir()
            (source / 'alias.rb').symlink_to('/not-a-real-source')
            with self.assertRaisesRegex(ValueError, 'SYMLINK_IN_RUBY_SOURCE'):
                M.pure_ruby(source, target)

    def test_collision_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'src', Path(tmp) / 'out'
            source.mkdir()
            target.mkdir()
            (source / 'a.rb').write_text('# fixture')
            (target / 'a.rb').write_text('# existing')
            with self.assertRaisesRegex(ValueError, 'STDLIB_COLLISION'):
                M.pure_ruby(source, target)

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'FRESH_OUTPUT_REQUIRED'):
                M.prepare({}, Path(tmp), Path(tmp), Path(tmp), Path(tmp), Path(tmp), Path(tmp))


if __name__ == '__main__':
    unittest.main()
