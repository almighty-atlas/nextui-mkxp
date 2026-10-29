# SPDX-License-Identifier: MIT
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import h700_environment as E


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roots = {}
        for key in E.COMPONENTS:
            path = self.root / key
            path.mkdir()
            (path / 'input').write_bytes(b'synthetic component')
            self.roots[key] = path
        self.archive = self.root / 'archive'
        self.archive.write_bytes(b'synthetic archive')

    def capture(self):
        with patch.object(E, 'COMPILER_ARCHIVE', E.sha(self.archive)), \
                patch.object(E, 'image_identity', return_value={'id': E.IMAGE, 'packages': ['fixture 1']}):
            return E.capture(self.roots, self.archive)

    def test_capture_and_match_do_not_clear_rebuild_or_rights(self):
        receipt = self.capture()
        self.assertEqual(E.compare(receipt, self.capture())['status'], 'ENVIRONMENT_MATCH')
        self.assertEqual(receipt['clean_room_rebuild'], 'NOT_VERIFIED')
        self.assertEqual(receipt['distribution'], 'BLOCKED')
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_archive_match_cannot_hide_extracted_compiler_change(self):
        receipt = self.capture()
        (self.roots['toolchain'] / 'input').write_bytes(b'changed compiler')
        with self.assertRaisesRegex(ValueError, 'ENVIRONMENT_DRIFT'):
            E.compare(receipt, self.capture())

    def test_every_other_component_is_bound(self):
        for key in ('sysroot', 'native', 'sdl'):
            receipt = self.capture()
            path = self.roots[key] / 'input'
            path.write_bytes(path.read_bytes() + b'x')
            with self.assertRaisesRegex(ValueError, 'ENVIRONMENT_DRIFT'):
                E.compare(receipt, self.capture())

    def test_mode_empty_directory_and_link_target_are_bound(self):
        path = self.roots['toolchain']
        before = E.fingerprint(path)
        (path / 'input').chmod(0o700)
        self.assertNotEqual(before, E.fingerprint(path))
        before = E.fingerprint(path)
        (path / 'empty').mkdir()
        self.assertNotEqual(before, E.fingerprint(path))
        (path / 'alias').symlink_to('input')
        before = E.fingerprint(path)
        (path / 'alias').unlink()
        (path / 'alias').symlink_to('empty')
        self.assertNotEqual(before, E.fingerprint(path))

    def test_relocation_and_mtime_do_not_change_digest(self):
        left = self.roots['toolchain']
        right = self.roots['native']
        (left / 'input').touch()
        self.assertEqual(E.fingerprint(left), E.fingerprint(right))

    def test_special_file_is_never_opened(self):
        os.mkfifo(self.roots['sysroot'] / 'fifo')
        with self.assertRaisesRegex(ValueError, 'COMPONENT_SPECIAL_FILE'):
            E.fingerprint(self.roots['sysroot'])

    def test_escaping_links_and_root_links_rejected(self):
        path = self.roots['sdl']
        (path / 'escape').symlink_to(self.archive)
        with self.assertRaisesRegex(ValueError, 'COMPONENT_LINK_ESCAPE'):
            E.fingerprint(path)
        alias = self.root / 'root-link'
        alias.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'INVALID_COMPONENT_ROOT'):
            E.fingerprint(alias)

    def test_package_and_image_identity_drift_rejected(self):
        receipt = self.capture()
        for field in ('id', 'packages'):
            changed = copy.deepcopy(receipt)
            changed['image'][field] = 'different'
            with self.assertRaisesRegex(ValueError, 'ENVIRONMENT_DRIFT'):
                E.compare(receipt, changed)

    def test_bad_archive_stops_before_docker(self):
        with patch.object(E, 'image_identity') as inspect:
            with self.assertRaisesRegex(ValueError, 'COMPILER_ARCHIVE_HASH'):
                E.capture(self.roots, self.archive)
            inspect.assert_not_called()

    def test_changed_input_during_capture_is_rejected(self):
        def mutate():
            (self.roots['sysroot'] / 'input').write_bytes(b'changed during inspection')
            return {'id': E.IMAGE}
        with patch.object(E, 'COMPILER_ARCHIVE', E.sha(self.archive)), \
                patch.object(E, 'image_identity', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'ENVIRONMENT_CHANGED_DURING_CAPTURE'):
                E.capture(self.roots, self.archive)

    def test_existing_receipt_preserved_without_docker(self):
        receipt = self.root / 'existing.json'
        receipt.write_text('private sentinel')
        command = [sys.executable, str(ROOT / 'scripts/h700_environment.py'), 'capture']
        for key, value in self.roots.items():
            command += ['--' + key, str(value)]
        result = subprocess.run(command + ['--compiler-archive', str(self.archive),
                                          '--receipt', str(receipt)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout), {'status': 'ENVIRONMENT_BLOCKED', 'code': 'RECEIPT_EXISTS'})
        self.assertNotIn('private sentinel', result.stdout + result.stderr)
        self.assertEqual(receipt.read_text(), 'private sentinel')

    def test_container_profile_has_no_network_credentials_or_target_execution(self):
        with patch.object(E, 'run', side_effect=[f'"{E.IMAGE}" "linux" "amd64"\n', 'fixture 1\n']) as run:
            E.image_identity()
        command = run.call_args.args[0]
        for flag in ('--network=none', '--read-only', '--pull=never', '--cpus=2',
                     '--memory=4g', '--memory-swap=4g', '--cap-drop=ALL', '--security-opt=no-new-privileges'):
            self.assertIn(flag, command)
        self.assertNotIn('--privileged', command)
        self.assertEqual(command[-1], E.TOOLS_SCRIPT)
