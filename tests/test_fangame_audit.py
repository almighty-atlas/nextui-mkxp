# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import rmxp_fangame_audit as A


def marshal_int(value):
    if value == 0:
        return b'\0'
    if 0 < value < 123:
        return bytes([value + 5])
    size = (value.bit_length() + 7) // 8
    return bytes([size]) + value.to_bytes(size, 'little')


def string(data):
    return b'"' + marshal_int(len(data)) + data


def scripts(code):
    return (b'\x04\x08[' + marshal_int(1) + b'[' + marshal_int(3) +
            b'i\0' + string(b'Synthetic') + string(zlib.compress(code)))


def packed(entries):
    result, key = bytearray(b'RGSSAD\0\x01'), 0xDEADCAFE
    def advance():
        nonlocal key
        current, key = key, (key * 7 + 3) & 0xffffffff
        return current
    for name, data in entries:
        name = name.encode()
        result.extend(struct.pack('<I', len(name) ^ advance()))
        result.extend(c ^ (advance() & 255) for c in name)
        result.extend(struct.pack('<I', len(data) ^ advance()))
        data_key = key
        for offset in range(0, len(data), 4):
            chunk = data[offset:offset + 4]
            value = int.from_bytes(chunk, 'little') ^ data_key
            result.extend(value.to_bytes(4, 'little')[:len(chunk)])
            data_key = (data_key * 7 + 3) & 0xffffffff
    return bytes(result)


class FangameAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.game = Path(self.temp.name)
        (self.game / 'Data').mkdir()
        (self.game / 'Scripts').mkdir()

    def test_loose_table_and_external_scripts_are_counted_without_execution(self):
        sentinel = self.game / 'MUST_NOT_EXIST'
        (self.game / 'Data/Scripts.rxdata').write_bytes(scripts(b'Input.press?(Input::D)'))
        (self.game / 'Scripts/external.rb').write_bytes(
            b'Win32API.new("test","test")\nGraphics.time_passed\nrequire "socket"\n' +
            ('File.write("' + str(sentinel) + '", "executed")').encode())
        report = A.audit(self.game)
        self.assertEqual(report['table_entries'], 1)
        self.assertEqual(report['loose_ruby_files'], 1)
        self.assertEqual(report['flags']['win32api'], 1)
        self.assertEqual(report['flags']['socket'], 1)
        self.assertIn('D', report['input_constants_referenced'])
        self.assertIn('time_passed', report['api_names_referenced']['Graphics'])
        self.assertFalse(sentinel.exists())
        self.assertFalse(report['ruby_executed'])
        self.assertNotIn('File.write', str(report))

    def test_rgss1_script_table_decoded_only_in_memory(self):
        path = self.game / 'Game.rgssad'
        table = scripts(b'Input::B; System.platform')
        path.write_bytes(packed([('Graphics/fixture.dat', b'not exported'),
                                 ('Data\\Scripts.rxdata', table), ('Data/other', b'trailing')]))
        original = path.read_bytes()
        decoded, count = A.scripts_from_rgss1(path)
        self.assertEqual(decoded, table)
        self.assertEqual(count, 3)
        report = A.audit(self.game)
        self.assertEqual(report['layout'], 'RGSSAD_V1')
        self.assertIn('platform', report['api_names_referenced']['System'])
        self.assertFalse((self.game / 'Data/Scripts.rxdata').exists())
        self.assertEqual(path.read_bytes(), original)

    def test_truncated_archive_and_bad_versions_fail(self):
        path = self.game / 'Game.rgssad'
        valid = packed([('Data/Scripts.rxdata', scripts(b'fixture'))])
        for data in (b'RGSSAD\0\x03', valid[:-1], valid[:12]):
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                A.scripts_from_rgss1(path)

    def test_unsafe_names_duplicates_and_native_name_buffer_limit(self):
        path = self.game / 'Game.rgssad'
        cases = [[('../escape', b'x')], [('A', b'x'), ('a', b'y')], [('x' * 512, b'x')]]
        for entries in cases:
            path.write_bytes(packed(entries))
            with self.assertRaises(ValueError):
                A.scripts_from_rgss1(path)

    def test_bounded_decompression_and_trailing_data(self):
        with patch.object(A, 'MAX_SCRIPT', 64):
            with self.assertRaises(ValueError):
                A.inflate(zlib.compress(b'x' * 1000))
        for data in (zlib.compress(b'x') + b'trailing', zlib.compress(b'x')[:-1]):
            with self.assertRaises(ValueError):
                A.inflate(data)

    def test_external_script_link_cannot_read_outside_game(self):
        (self.game / 'Data/Scripts.rxdata').write_bytes(scripts(b'fixture'))
        (self.game / 'Scripts/external.rb').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            A.audit(self.game)
