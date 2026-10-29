# SPDX-License-Identifier: MIT
"""Synthetic Marshal fixtures only; no game, RTP or proprietary data."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rgss_inventory', ROOT / 'scripts/rgss_inventory.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class Raw(bytes):
    """Pre-encoded Marshal bytes inserted verbatim."""


class Encoder:
    """Minimal Ruby Marshal 4.8 writer for test fixtures."""

    def __init__(self):
        self.symbols = {}

    def long(self, n):
        if n == 0:
            return b'\x00'
        if 0 < n < 123:
            return bytes([n + 5])
        if -124 < n < 0:
            return bytes([(n - 5) & 0xff])
        raw = n.to_bytes(4, 'little', signed=True).rstrip(b'\x00' if n > 0 else b'\xff')
        return bytes([len(raw) if n > 0 else 256 - len(raw)]) + raw

    def sym(self, name):
        if name in self.symbols:
            return b';' + self.long(self.symbols[name])
        self.symbols[name] = len(self.symbols)
        raw = name.encode()
        return b':' + self.long(len(raw)) + raw

    def obj(self, value):
        if value is None:
            return b'0'
        if value is True or value is False:
            return b'T' if value else b'F'
        if isinstance(value, int):
            return b'i' + self.long(value)
        if isinstance(value, str):
            raw = value.encode()
            return b'"' + self.long(len(raw)) + raw
        if isinstance(value, Raw):
            return bytes(value)
        if isinstance(value, bytes):
            return b'"' + self.long(len(value)) + value
        if isinstance(value, list):
            return b'[' + self.long(len(value)) + b''.join(self.obj(v) for v in value)
        if isinstance(value, dict):
            return b'{' + self.long(len(value)) + b''.join(self.obj(k) + self.obj(v) for k, v in value.items())
        cls, ivars = value
        return (b'o' + self.sym(cls) + self.long(len(ivars)) +
                b''.join(self.sym(k) + self.obj(v) for k, v in ivars.items()))

    def dump(self, value):
        self.symbols = {}
        return b'\x04\x08' + self.obj(value)


def audio(name):
    return ('RPG::AudioFile', {'@name': name, '@volume': 100, '@pitch': 100})


def command(code, params):
    return ('RPG::EventCommand', {'@code': code, '@indent': 0, '@parameters': params})


class RgssInventory(unittest.TestCase):
    def project(self, temp, scripts=b'p 1\n'):
        game, rtp = Path(temp) / 'game', Path(temp) / 'rtp'
        enc = Encoder()
        (game / 'Data').mkdir(parents=True)
        for folder, name in (('Graphics/Characters', 'Hero.png'), ('Audio/BGM', 'Theme.ogg'),
                             ('Graphics/Pictures', 'logo.PNG')):
            (game / folder).mkdir(parents=True, exist_ok=True)
            (game / folder / name).write_bytes(b'synthetic')
        for folder, name in (('Audio/SE', '001-System01.ogg'), ('Graphics/Tilesets', '001-Grassland01.png'),
                             ('Audio/BGM', 'Theme.mid')):
            (rtp / folder).mkdir(parents=True, exist_ok=True)
            (rtp / folder / name).write_bytes(b'synthetic')
        actors = [None, ('RPG::Actor', {'@character_name': 'Hero', '@battler_name': ''})]
        tilesets = [None, ('RPG::Tileset', {'@tileset_name': '001-Grassland01',
                                            '@autotile_names': ['', 'Missing-Water']})]
        route = ('RPG::MoveRoute', {'@list': [('RPG::MoveCommand', {'@code': 44, '@parameters': [audio('001-System01')]})]})
        page = ('RPG::Event::Page', {'@list': [command(241, [audio('Theme')]), command(231, [1, 'Logo']),
                                               command(209, [-1, route]), command(0, [])]})
        system = ('RPG::System', {'@cursor_se': audio('001-System01'), '@title_bgm': audio('Theme')})
        (game / 'Data/Actors.rxdata').write_bytes(enc.dump(actors))
        (game / 'Data/Tilesets.rxdata').write_bytes(enc.dump(tilesets))
        (game / 'Data/Map001.rxdata').write_bytes(enc.dump(('RPG::Map', {'@events': {1: ('RPG::Event', {'@pages': [page]})}})))
        (game / 'Data/System.rxdata').write_bytes(enc.dump(system))
        (game / 'Data/Scripts.rxdata').write_bytes(enc.dump([[1, 'Main', zlib.compress(scripts)]]))
        return game, rtp

    def test_references_resolve_against_game_then_rtp(self):
        with tempfile.TemporaryDirectory() as temp:
            game, rtp = self.project(temp)
            report = M.inventory(game, [rtp])
        rows = {(r['category'], r['name']): r for r in report['rows']}
        self.assertEqual(rows[('Graphics/Characters', 'Hero')]['origin'], 'game')
        self.assertEqual(rows[('Audio/BGM', 'Theme')]['file'], 'Audio/BGM/Theme.ogg')
        self.assertEqual(rows[('Graphics/Tilesets', '001-Grassland01')]['origin'], 'rtp')
        self.assertEqual(rows[('Audio/SE', '001-System01')]['origin'], 'rtp')
        self.assertEqual(rows[('Graphics/Autotiles', 'Missing-Water')]['origin'], 'missing')
        self.assertFalse(rows[('Graphics/Pictures', 'Logo')]['case_exact'])
        self.assertEqual(report['resolved'], {'game': 3, 'rtp': 2, 'missing': 1, 'case_mismatch': 1})
        self.assertTrue(report['rtp_required'])
        self.assertNotIn(('Graphics/Battlers', ''), rows)

    def test_script_flags_and_literal_references(self):
        source = (b'x = Win32API.new("user32", "GetAsyncKeyState", "i", "i")\n'
                  b'b = RPG::Cache.picture("Banner")\nAudio.se_play("Audio/SE/Click", 80)\n')
        with tempfile.TemporaryDirectory() as temp:
            game, rtp = self.project(temp, source)
            report = M.inventory(game, [rtp])
        self.assertEqual(report['scripts']['win32api_calls'], ['user32:GetAsyncKeyState'])
        self.assertEqual(report['scripts']['flags']['win32api'], 1)
        names = {(r['category'], r['name']) for r in report['rows']}
        self.assertIn(('Graphics/Pictures', 'Banner'), names)
        self.assertIn(('Audio/SE', 'Click'), names)

    def test_marshal_links_symlinks_and_integers(self):
        enc = Encoder()
        shared = ('RPG::AudioFile', {'@name': 'A'})
        data = enc.dump([shared, Raw(b'@\x06'), 300, -300, 70000, ('RPG::AudioFile', {'@name': 'B'})])
        value = M.Marshal(data).load()
        self.assertIs(value[1], value[0])
        self.assertEqual(value[2:5], [300, -300, 70000])
        self.assertEqual(value[5].cls, 'RPG::AudioFile')

    def test_guards(self):
        with self.assertRaisesRegex(ValueError, 'MARSHAL_VERSION'):
            M.Marshal(b'\x04\x090').load()
        with self.assertRaisesRegex(ValueError, 'MARSHAL_TRAILING_DATA'):
            M.Marshal(b'\x04\x0800').load()
        with self.assertRaisesRegex(ValueError, 'MARSHAL_TOO_DEEP'):
            M.Marshal(b'\x04\x08' + b'[\x06' * 300 + b'0').load()
        with self.assertRaisesRegex(ValueError, 'MARSHAL_BAD_LINK'):
            M.Marshal(b'\x04\x08@\x06').load()
        with tempfile.TemporaryDirectory() as temp:
            game, rtp = self.project(temp)
            (game / 'Game.rgssad').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError, 'ENCRYPTED_ARCHIVE_UNSUPPORTED'):
                M.inventory(game, [rtp])
            (game / 'Game.rgssad').unlink()
            (game / 'Graphics/link').symlink_to(game / 'Data')
            with self.assertRaisesRegex(ValueError, 'SYMLINK_REFUSED'):
                M.inventory(game, [rtp])

    def test_recorded_knight_blade_evidence_is_consistent(self):
        import json
        evidence = json.loads((ROOT / 'build/h700-engine/knight-blade-inventory.json').read_text())
        inv = evidence['inventory']
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / inv['tool']).read_bytes()).hexdigest(), inv['tool_sha256'])
        self.assertEqual(sum(inv['resolved'][k] for k in ('game', 'rtp', 'missing')), inv['references'])
        self.assertEqual(sum(inv['rtp_by_category'].values()), inv['resolved']['rtp'])
        self.assertEqual(sum(inv['resolved_extensions'].values()), inv['resolved']['game'] + inv['resolved']['rtp'])
        self.assertEqual(sum(inv['midi_references'].values()), inv['resolved_extensions']['.mid'])
        self.assertEqual(len(inv['missing']), inv['resolved']['missing'])
        self.assertFalse(evidence['provenance']['rtp']['executed'])
        self.assertFalse(evidence['game_or_rtp_bytes_in_repository'])
        self.assertFalse(evidence['scripts']['source_committed'])
        tracked = M.Path(ROOT).glob('**/*')
        banned = ('.rxdata', '.rgssad', '.mid', '.ogg', '.wav', '.exe', '.dll')
        self.assertFalse([p for p in tracked if p.suffix.lower() in banned and '.git' not in p.parts])


if __name__ == '__main__':
    unittest.main()
