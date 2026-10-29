# SPDX-License-Identifier: MIT
"""Synthetic wrap fixtures only. No network, clone or engine source."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
SPEC = importlib.util.spec_from_file_location('source_lock', SCRIPTS / 'mkxp_z_source_lock.py')
M = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(M)
finally:
    sys.path.remove(str(SCRIPTS))

HASH = 'a' * 64
COMMIT = 'b' * 40


class SourceLock(unittest.TestCase):
    def tree(self, tmp, wraps):
        sub = Path(tmp) / 'subprojects'
        (sub / 'packagefiles/zdir').mkdir(parents=True)
        (sub / 'packagefiles/zdir/meson.build').write_text('# fixture\n')
        (sub / 'packagefiles/z.patch').write_text('# fixture patch\n')
        for name, text in wraps.items():
            (sub / (name + '.wrap')).write_text(text)
        return Path(tmp)

    def file_wrap(self, url='https://example.invalid/z.tar.gz', digest=HASH):
        return ('[wrap-file]\ndirectory = z-1\nsource_url = ' + url +
                '\nsource_hash = ' + digest +
                '\npatch_directory = zdir\ndiff_files =\n    z.patch\n')

    def git_wrap(self):
        return ('[wrap-git]\nurl = https://example.invalid/img\nrevision = release-1\n'
                'depth = 1\nclone-recursive = true\n')

    def profile(self, wraps, excluded=(), pins=None):
        return {'commit': COMMIT, 'wraps': list(wraps), 'excluded_wraps': list(excluded),
                'git_pins': pins or {}}

    def test_complete_file_wrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, {'z': self.file_wrap(), 'x11': self.file_wrap()})
            r = M.lock(root, self.profile(['z'], ['x11']))
            self.assertEqual(r['status'], 'LOCK_COMPLETE', r['issues'])
            z = r['wraps']['z']
            self.assertEqual(z['filename'], 'z.tar.gz')
            self.assertEqual(z['diff_files']['z.patch'],
                             hashlib.sha256(b'# fixture patch\n').hexdigest())
            self.assertIn('patch_directory_tree_sha256', z)

    def test_unclassified_and_stale_wraps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, {'z': self.file_wrap(), 'new': self.file_wrap()})
            r = M.lock(root, self.profile(['z'], ['gone']))
            self.assertIn('UNCLASSIFIED_WRAP:new', r['issues'])
            self.assertIn('STALE_EXCLUSION:gone', r['issues'])
            self.assertEqual(r['status'], 'LOCK_INCOMPLETE')

    def test_hash_and_https_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, {'z': self.file_wrap('http://example.invalid/z.tgz', '')})
            issues = M.lock(root, self.profile(['z']))['issues']
            self.assertIn('ARCHIVE_HASH_MISSING:z', issues)
            self.assertIn('NON_HTTPS_URL:z', issues)

    def test_wrapdb_overlay_is_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = self.file_wrap() + ('patch_url = https://example.invalid/o\n'
                                       'patch_filename = o.zip\npatch_hash = ' + 'c' * 64 + '\n')
            r = M.lock(self.tree(tmp, {'z': text}), self.profile(['z']))
            self.assertEqual(r['issues'], [])
            self.assertEqual(r['wraps']['z']['patch_archive'],
                             {'urls': ['https://example.invalid/o'], 'sha256': 'c' * 64,
                              'filename': 'o.zip'})
        with tempfile.TemporaryDirectory() as tmp:
            text = self.file_wrap() + 'patch_url = http://example.invalid/o.zip\n'
            issues = M.lock(self.tree(tmp, {'z': text}), self.profile(['z']))['issues']
            self.assertIn('ARCHIVE_HASH_MISSING:z:overlay', issues)
            self.assertIn('NON_HTTPS_URL:z:overlay', issues)

    def test_unknown_wrap_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = self.file_wrap() + 'lead_directory_missing = true\n'
            self.assertIn('UNKNOWN_WRAP_KEY:z:lead_directory_missing',
                          M.lock(self.tree(tmp, {'z': text}), self.profile(['z']))['issues'])

    def test_missing_patch_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, {'z': self.file_wrap()})
            (root / 'subprojects/packagefiles/z.patch').unlink()
            self.assertIn('DIFF_FILE_MISSING:z:z.patch',
                          M.lock(root, self.profile(['z']))['issues'])

    def test_git_tag_requires_commit_and_submodules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, {'img': self.git_wrap()})
            issues = M.lock(root, self.profile(['img']))['issues']
            self.assertIn('MUTABLE_GIT_REVISION:img', issues)
            self.assertIn('SUBMODULES_UNRECORDED:img', issues)
            pins = {'img': {'commit': COMMIT, 'submodules': {'external/png': 'c' * 40}}}
            self.assertEqual(M.lock(root, self.profile(['img'], pins=pins))['issues'], [])

    def test_cached_archive_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'z.tar.gz'
            path.write_bytes(b'fixture')
            good = hashlib.sha256(b'fixture').hexdigest()
            self.assertEqual(M.download(['https://unused.invalid/z'], good, path), 'CACHED')
            with self.assertRaisesRegex(ValueError, 'CACHED_ARCHIVE_HASH_MISMATCH'):
                M.download(['https://unused.invalid/z'], HASH, path)

    def test_download_rejects_wrong_hash_and_plain_http(self):
        class Response:
            def __init__(self):
                self.data = [b'unexpected', b'']

            def geturl(self):
                return 'https://example.invalid/z'

            def read(self, _):
                return self.data.pop(0)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'z.tar.gz'
            with patch.object(M.urllib.request, 'urlopen', return_value=Response()):
                with self.assertRaisesRegex(ValueError, 'DOWNLOAD_FAILED'):
                    M.download(['https://example.invalid/z'], HASH, target)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])
            with self.assertRaisesRegex(ValueError, 'NON_HTTPS_URL'):
                M.download(['http://example.invalid/z'], HASH, target)

    def test_repository_profile_is_consistent(self):
        profile = json.loads((ROOT / 'build/h700-engine/mkxp-z-profile.json').read_text())
        self.assertFalse(set(profile['wraps']) & set(profile['excluded_wraps']))
        self.assertEqual(profile['meson_options']['sdl_system'], 'enabled')
        self.assertEqual(profile['meson_options']['ruby_system'], 'disabled')
        self.assertEqual(profile['meson_options']['extra_shaders'], 'disabled')
        self.assertIn('sdl2', profile['excluded_wraps'])


if __name__ == '__main__':
    unittest.main()
