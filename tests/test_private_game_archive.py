# SPDX-License-Identifier: MIT
import importlib.util
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('private_archive', ROOT / 'scripts/rmxp_private_archive.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


class PrivateArchive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'game.zip'
        self.output = self.root / 'private'
        # Tiny synthetic fixtures run on bounded CI tmpfs, not a 6-GiB volume.
        usage = A.shutil.disk_usage(self.root)._replace(free=20 * A.GIB)
        space = patch.object(A.shutil, 'disk_usage', return_value=usage)
        space.start()
        self.addCleanup(space.stop)

    def make(self, files):
        with zipfile.ZipFile(self.archive, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in files:
                archive.writestr(name, content)
        return A.digest(self.archive)

    def test_inspection_is_readonly_and_extraction_preserves_bytes(self):
        expected = self.make([('Game ü/Game.ini', '[Game]\n'), ('Game ü/Game.exe', b'MZ-synthetic')])
        before = self.archive.read_bytes()
        result = A.process(self.archive, expected)
        self.assertEqual(result['game_roots'], ['Game ü'])
        self.assertFalse(self.output.exists())
        result = A.process(self.archive, expected, self.output)
        self.assertEqual(result['target_execution'], 'NEVER')
        self.assertEqual(result['h700_result'], 'NOT_TESTED')
        self.assertEqual((self.output / 'Game ü/Game.exe').read_bytes(), b'MZ-synthetic')
        self.assertFalse((self.output / 'Game ü/Game.exe').stat().st_mode & 0o111)
        self.assertEqual(self.archive.read_bytes(), before)

    def test_bad_hash_writes_nothing(self):
        self.make([('Game.ini', 'fixture')])
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_HASH'):
            A.process(self.archive, '0' * 64, self.output)
        self.assertFalse(self.output.exists())

    def test_unsafe_paths_rejected_before_output(self):
        for name in ('../outside', '/outside', 'C:/outside', 'a\\b', 'a/./b', 'a//b', 'x\nname',
                     'AUX.txt', 'test./file', 'test /file'):
            expected = self.make([(name, 'synthetic')])
            with self.assertRaises(ValueError, msg=name):
                A.process(self.archive, expected, self.output)
            self.assertFalse(self.output.exists())

    def test_duplicates_case_and_implicit_parent_collisions(self):
        cases = [[('same', '1'), ('same', '2')], [('A.png', '1'), ('a.png', '2')],
                 [('Data/a', '1'), ('data/b', '2')], [('Data', '1'), ('Data/a', '2')]]
        for files in cases:
            expected = self.make(files)
            with self.assertRaises(ValueError):
                A.process(self.archive, expected, self.output)
            self.assertFalse(self.output.exists())

    def test_links_and_special_files_rejected(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR):
            info = zipfile.ZipInfo('link')
            info.create_system = 3
            info.external_attr = (kind | 0o600) << 16
            with zipfile.ZipFile(self.archive, 'w') as archive:
                archive.writestr(info, 'outside')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_SPECIAL_FILE'):
                A.process(self.archive, A.digest(self.archive), self.output)

    def test_existing_destination_preserved(self):
        expected = self.make([('Game.ini', 'fixture')])
        self.output.mkdir()
        (self.output / 'keep').write_text('existing')
        with self.assertRaisesRegex(ValueError, 'FRESH_OUTPUT_REQUIRED'):
            A.process(self.archive, expected, self.output)
        self.assertEqual((self.output / 'keep').read_text(), 'existing')

    def test_limits_and_space_guard(self):
        expected = self.make([('Game.ini', 'fixture')])
        for name, limit in (('MAX_FILES', 0), ('MAX_TOTAL', 1), ('MAX_FILE', 1)):
            with patch.object(A, name, limit):
                with self.assertRaises(ValueError):
                    A.process(self.archive, expected, self.output)
        usage = A.shutil.disk_usage(self.root)._replace(free=1)
        with patch.object(A.shutil, 'disk_usage', return_value=usage):
            with self.assertRaisesRegex(ValueError, 'FREE_SPACE_GUARD'):
                A.process(self.archive, expected, self.output)
        self.assertFalse(self.output.exists())

    def test_root_links_and_lower_reserve_rejected(self):
        expected = self.make([('Game.ini', 'fixture')])
        link = self.root / 'alias'
        link.symlink_to(self.archive)
        with self.assertRaisesRegex(ValueError, 'REGULAR_INPUT_REQUIRED'):
            A.process(link, expected)
        with self.assertRaisesRegex(ValueError, 'RESERVE_BELOW_APPROVAL'):
            A.process(self.archive, expected, self.output, reserve_gib=1)

    @unittest.skipUnless(A.ctypes.util.find_library('archive'), 'libarchive unavailable on this host')
    def test_synthetic_cab_uses_native_reader_without_executing_payload(self):
        content, name = b'[Game]\n', b'Game.ini\0'
        file_table = struct.pack('<IIHHHH', len(content), 0, 0, 0, 0, 0) + name
        data_offset = 36 + 8 + len(file_table)
        data_block = struct.pack('<IHH', 0, len(content), len(content)) + content
        header = struct.pack('<4sIIIIIBBHHHHH', b'MSCF', 0, data_offset + len(data_block),
                             0, 44, 0, 3, 1, 1, 1, 0, 0, 0)
        self.archive.write_bytes(header + struct.pack('<IHH', data_offset, 1, 0) + file_table + data_block)
        result = A.process(self.archive, A.digest(self.archive), self.output)
        self.assertEqual(result['game_roots'], ['.'])
        self.assertEqual((self.output / 'Game.ini').read_bytes(), content)
