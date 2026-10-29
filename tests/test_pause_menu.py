# SPDX-License-Identifier: MIT
"""Run the Ruby pause-menu tests when a Ruby 3.1+ interpreter is available."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUBY = os.environ.get('RMXP_RUBY') or shutil.which('ruby')


@unittest.skipUnless(RUBY, 'Ruby 3.1+ unavailable; set RMXP_RUBY')
class PauseMenuRubyTests(unittest.TestCase):
    def test_ruby_suite(self):
        result = subprocess.run([RUBY, '-I', str(ROOT / 'rgss'),
                                 str(ROOT / 'tests/pause_menu_test.rb'), '-v'],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-2000:])
        self.assertIn(' 0 failures, 0 errors', result.stdout)


if __name__ == '__main__':
    unittest.main()
