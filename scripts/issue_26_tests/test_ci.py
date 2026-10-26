from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from issue_26_ci import check_whitespace


class BranchWhitespaceTests(unittest.TestCase):
    def test_earlier_commit_is_checked_on_push_and_pr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                                                '-c', 'commit.gpgsign=false', '-C', directory, *args],
                                               text=True, stderr=subprocess.PIPE).strip()
            git('init', '-q')
            git('config', 'user.name', 'Offline Test')
            git('config', 'user.email', 'offline@example.invalid')
            (root/'base').write_text('base\n')
            git('add', '.'); git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            git('update-ref', 'refs/remotes/origin/main', base)
            (root/'earlier').write_text('trailing whitespace \n')
            git('add', '.'); git('commit', '-qm', 'earlier change')
            (root/'later').write_text('clean later change\n')
            git('add', '.'); git('commit', '-qm', 'later change')
            self.assertEqual(git('diff', '--check', 'HEAD^', 'HEAD'), '')
            for ref in (base, 'refs/remotes/origin/main'):
                with self.subTest(event_base=ref):
                    common, result = check_whitespace(root, ref)
                    self.assertEqual(common, base)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('earlier:1', result.stdout)
            (root/'earlier').write_text('fixed\n')
            git('add', '.'); git('commit', '-qm', 'fix original whitespace')
            self.assertEqual(check_whitespace(root, base)[1].returncode, 0)

    def test_missing_base_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['git', 'init', '-q', directory], check=True)
            with self.assertRaises(subprocess.CalledProcessError):
                check_whitespace(directory, 'refs/remotes/origin/missing')
