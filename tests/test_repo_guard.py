# SPDX-License-Identifier: MIT
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'scripts/repo_guard.py'
SENTINEL = 'PRIVATE_SENTINEL_7f3a'


class RepoGuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env = dict(env, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        self.git('init', '-q')
        for name in ('README.md', 'AGENTS.md', 'docs/ROADMAP.md', 'docs/ARCHITECTURE.md',
                     'docs/TEST_PLAN.md', 'docs/COMPATIBILITY.md', '.gitignore'):
            self.write(name, '# fixture\n')
        self.write('README.md', '[Plan](docs/ROADMAP.md) [Web](https://example.invalid) [Top](#x)\n')
        self.git('add', '-A')

    def git(self, *args):
        subprocess.run(['git', *args], cwd=self.repo, env=self.env, check=True, capture_output=True)

    def write(self, name, data):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        (path.write_bytes if isinstance(data, bytes) else path.write_text)(data)
        return path

    def stage(self, name, data):
        self.write(name, data)
        self.git('add', '-f', '--', name)

    def run_guard(self, *args):
        return subprocess.run(['python3', '-I', str(GUARD), *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, timeout=30)

    def rules(self):
        result = self.run_guard('--json')
        self.assertNotIn(SENTINEL, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1 if report['findings'] else 0)
        return {(f['rule'], f['path']) for f in report['findings']}

    def test_clean_fixture_passes(self):
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('REPO_GUARD=PASS', result.stdout)

    def test_staged_game_bundle_fails_without_leaking_contents(self):
        self.stage('games/Knight Blade/Data/Map001.rxdata', b'\x04\x08' + SENTINEL.encode())
        self.stage('games/Knight Blade/Game.ini', '[Game]\nTitle=' + SENTINEL + '\n')
        self.stage('docs/Graphics/Characters/hero.png', SENTINEL)
        self.stage('Game.rgssad', b'RGSSAD\x00' + SENTINEL.encode())
        found = self.rules()
        for expected in [('GAME_DATA_OR_ROM', 'games/Knight Blade/Data/Map001.rxdata'),
                         ('RUBY_MARSHAL', 'games/Knight Blade/Data/Map001.rxdata'),
                         ('GAME_DIRECTORY', 'games/Knight Blade/Game.ini'),
                         ('GAME_EXECUTABLE_OR_CONFIG', 'games/Knight Blade/Game.ini'),
                         ('RMXP_ASSET_DIRECTORY', 'docs/Graphics/Characters/hero.png'),
                         ('RGSS_ARCHIVE', 'Game.rgssad')]:
            self.assertIn(expected, found)
        text = self.run_guard()
        self.assertEqual(text.returncode, 1)
        self.assertNotIn(SENTINEL, text.stdout)

    def test_binaries_archives_large_files_and_roms(self):
        self.stage('tools/engine', b'\x7fELF' + bytes(64))
        self.stage('notes/blob.bin', b'PK\x03\x04' + bytes(16))
        self.stage('docs/huge.txt', 'x' * (256 * 1024 + 1))
        self.stage('docs/fixture.gba', b'synthetic')
        found = self.rules()
        self.assertTrue({('ELF_BINARY', 'tools/engine'), ('ZIP_ARCHIVE', 'notes/blob.bin'),
                         ('FILE_TOO_LARGE', 'docs/huge.txt'),
                         ('GAME_DATA_OR_ROM', 'docs/fixture.gba')} <= found)

    def test_secrets_are_reported_by_rule_only(self):
        header = '-----BEGIN ' + 'OPENSSH PRIVATE KEY-----'
        self.stage('docs/notes.md', header + '\n' + SENTINEL + '\n')
        self.stage('config/app.txt', 'token=' + 'ghp_' + 'A' * 36 + SENTINEL)
        self.stage('.env', 'X=' + SENTINEL)
        found = self.rules()
        self.assertTrue({('PRIVATE_KEY', 'docs/notes.md'), ('GITHUB_TOKEN', 'config/app.txt'),
                         ('CREDENTIAL_FILE', '.env')} <= found)

    def test_staged_version_is_checked_not_worktree(self):
        self.stage('docs/later.txt', 'token=' + 'ghp_' + 'B' * 36)
        self.write('docs/later.txt', 'clean now\n')
        self.assertIn(('GITHUB_TOKEN', 'docs/later.txt'), self.rules())

    def test_manifests_shell_links_symlinks_and_required_files(self):
        self.stage('build/manifest.json', '{"broken": ')
        self.stage('pak/launch.sh', '#!/bin/sh\nif then\n')
        self.stage('docs/GUIDE.md', '[Missing](NOPE.md) [Escape](../../etc/passwd)\n')
        os.symlink('/etc/hostname', self.repo / 'link')
        self.git('add', 'link')
        self.git('rm', '-q', '--cached', 'docs/TEST_PLAN.md')
        found = self.rules()
        self.assertTrue({('INVALID_JSON', 'build/manifest.json'), ('SHELL_SYNTAX', 'pak/launch.sh'),
                         ('BROKEN_MARKDOWN_LINK', 'docs/GUIDE.md'), ('SYMLINK', 'link'),
                         ('REQUIRED_FILE_MISSING', 'docs/TEST_PLAN.md')} <= found)

    def test_unicode_and_space_paths_are_quoted(self):
        self.stage('saves/Spielstand ü.txt', SENTINEL)
        result = self.run_guard()
        self.assertIn("FAIL GAME_DIRECTORY 'saves/Spielstand ü.txt'", result.stdout)

    def test_outside_git_repository_is_error(self):
        shutil.rmtree(self.repo / '.git')
        result = self.run_guard()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')

    def test_repository_itself_passes(self):
        result = subprocess.run(['python3', '-I', str(GUARD)], cwd=ROOT, capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == '__main__':
    unittest.main()
