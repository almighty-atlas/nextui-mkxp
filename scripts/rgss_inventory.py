#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only RPG Maker XP reference inventory. Never executes game scripts.

Parses Ruby Marshal 4.8 data with a minimal data-only reader (no object
construction), collects graphics/audio names referenced by database, map and
event data, resolves them against the game folder and optional RTP folders,
and flags script features that are platform-specific (e.g. Win32API).
Only names, counts and hashes are reported, never asset bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zlib

GRAPHIC_EXT = ('.png', '.jpg', '.jpeg', '.bmp')
AUDIO_EXT = ('.ogg', '.wav', '.mid', '.midi', '.mp3', '.wma')
IVAR_GRAPHICS = {
    '@character_name': 'Graphics/Characters', '@battler_name': 'Graphics/Battlers',
    '@icon_name': 'Graphics/Icons', '@animation_name': 'Graphics/Animations',
    '@tileset_name': 'Graphics/Tilesets', '@autotile_names': 'Graphics/Autotiles',
    '@panorama_name': 'Graphics/Panoramas', '@fog_name': 'Graphics/Fogs',
    '@battleback_name': 'Graphics/Battlebacks', '@windowskin_name': 'Graphics/Windowskins',
    '@title_name': 'Graphics/Titles', '@gameover_name': 'Graphics/Gameovers',
    '@battle_transition': 'Graphics/Transitions',
}
IVAR_AUDIO = {
    '@bgm': 'Audio/BGM', '@title_bgm': 'Audio/BGM', '@battle_bgm': 'Audio/BGM',
    '@bgs': 'Audio/BGS', '@battle_end_me': 'Audio/ME', '@gameover_me': 'Audio/ME',
}
COMMAND_AUDIO = {241: 'Audio/BGM', 245: 'Audio/BGS', 249: 'Audio/ME', 250: 'Audio/SE',
                 132: 'Audio/BGM', 133: 'Audio/ME'}
PANORAMA_FOG_BATTLEBACK = ('Graphics/Panoramas', 'Graphics/Fogs', 'Graphics/Battlebacks')
SCRIPT_FLAGS = {
    'win32api': re.compile(rb'Win32API'),
    'resize_screen': re.compile(rb'resize_screen'),
    'font_default_name': re.compile(rb'Font\.default_name'),
    'system_or_backtick': re.compile(rb'(?<![\w.])(system|exec|spawn)\s*\(|`'),
    'file_write': re.compile(rb'File\.open\([^)]*["\']w'),
    'save_files': re.compile(rb'Save\d|\.rxdata'),
}
WIN32API_CALL = re.compile(rb'Win32API\.new\(\s*["\']([\w.]+)["\']\s*,\s*["\'](\w+)["\']')
CACHE_LITERAL = re.compile(rb'RPG::Cache\.(\w+)\(\s*["\']([^"\']+)["\']')
AUDIO_LITERAL = re.compile(rb'Audio\.(bgm|bgs|me|se)_play\(\s*["\']Audio/(\w+)/([^"\']+)["\']')
CACHE_DIRS = {'animation': 'Animations', 'autotile': 'Autotiles', 'battleback': 'Battlebacks',
              'battler': 'Battlers', 'character': 'Characters', 'fog': 'Fogs',
              'gameover': 'Gameovers', 'icon': 'Icons', 'panorama': 'Panoramas',
              'picture': 'Pictures', 'tileset': 'Tilesets', 'title': 'Titles',
              'windowskin': 'Windowskins'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


class Obj(dict):
    """Marshalled Ruby object: class name plus instance variables."""
    def __init__(self, cls):
        super().__init__()
        self.cls = cls


class Marshal:
    """Data-only Ruby Marshal 4.8 reader with recursion and size guards."""

    def __init__(self, data, max_depth=200):
        self.data, self.pos, self.depth, self.max_depth = data, 0, 0, max_depth
        self.symbols, self.objects = [], []

    def byte(self):
        require(self.pos < len(self.data), 'MARSHAL_TRUNCATED')
        self.pos += 1
        return self.data[self.pos - 1]

    def bytes(self, n):
        require(0 <= n <= len(self.data) - self.pos, 'MARSHAL_TRUNCATED')
        self.pos += n
        return self.data[self.pos - n:self.pos]

    def long(self):
        c = self.byte()
        c = c - 256 if c > 127 else c
        if c == 0:
            return 0
        if 5 <= c:
            return c - 5
        if c <= -5:
            return c + 5
        raw = self.bytes(abs(c))
        value = int.from_bytes(raw, 'little')
        return value if c > 0 else value - (1 << (8 * -c))

    def symbol(self):
        t = chr(self.byte())
        if t == ';':
            index = self.long()
            require(0 <= index < len(self.symbols), 'MARSHAL_BAD_SYMLINK')
            return self.symbols[index]
        if t == 'I':
            name = self.symbol()
            self.ivars()
            return name
        require(t == ':', 'MARSHAL_SYMBOL_EXPECTED')
        name = self.bytes(self.long()).decode('utf-8', 'replace')
        self.symbols.append(name)
        return name

    def register(self, value):
        self.objects.append(value)
        return len(self.objects) - 1

    def ivars(self, target=None):
        for _ in range(self.long()):
            key, value = self.symbol(), self.read()
            if target is not None:
                target[key] = value

    def load(self):
        require(self.bytes(2) == b'\x04\x08', 'MARSHAL_VERSION')
        value = self.read()
        require(self.pos == len(self.data), 'MARSHAL_TRAILING_DATA')
        return value

    def read(self):
        self.depth += 1
        require(self.depth <= self.max_depth, 'MARSHAL_TOO_DEEP')
        try:
            return self._read(chr(self.byte()))
        finally:
            self.depth -= 1

    def _read(self, t):
        if t == '0':
            return None
        if t in 'TF':
            return t == 'T'
        if t == 'i':
            return self.long()
        if t in ':;':
            self.pos -= 1
            return self.symbol()
        if t == '@':
            index = self.long()
            require(0 <= index < len(self.objects), 'MARSHAL_BAD_LINK')
            return self.objects[index]
        if t == 'I':
            value = self.read()
            self.ivars(value if isinstance(value, Obj) else None)
            return value
        if t == 'e':
            self.symbol()
            return self.read()
        if t == '"':
            value = self.bytes(self.long())
            self.register(value)
            return value
        if t == '/':
            value = self.bytes(self.long())
            self.byte()
            self.register(value)
            return value
        if t == 'f':
            value = self.bytes(self.long())
            self.register(value)
            return value
        if t == 'l':
            sign = self.byte()
            value = int.from_bytes(self.bytes(2 * self.long()), 'little')
            value = value if sign == ord('+') else -value
            self.register(value)
            return value
        if t == '[':
            value = []
            self.register(value)
            for _ in range(self.long()):
                value.append(self.read())
            return value
        if t in '{}':
            value = {}
            self.register(value)
            for _ in range(self.long()):
                key = self.read()
                value[key if isinstance(key, (int, str, bytes, bool, type(None))) else id(key)] = self.read()
            if t == '}':
                self.read()
            return value
        if t in 'oS':
            value = Obj(self.symbol())
            self.register(value)
            for _ in range(self.long()):
                key = self.symbol()
                value[key if t == 'o' else '@' + key] = self.read()
            return value
        if t == 'u':
            value = Obj(self.symbol())
            value['_dump'] = self.bytes(self.long())
            self.register(value)
            return value
        if t == 'C':
            self.symbol()
            return self.read()
        if t == 'U':
            value = Obj(self.symbol())
            self.register(value)
            value['_data'] = self.read()
            return value
        if t in 'cm':
            value = self.bytes(self.long()).decode('utf-8', 'replace')
            self.register(value)
            return value
        raise ValueError('MARSHAL_UNSUPPORTED_TYPE_' + t)


def text(value):
    return value.decode('utf-8', 'replace') if isinstance(value, bytes) else value


def audio_name(value):
    return text(value.get('@name')) if isinstance(value, Obj) else None


class Collector:
    def __init__(self):
        self.refs = {}
        self.seen = set()

    def add(self, category, name, source):
        name = text(name)
        if isinstance(name, str) and name.strip():
            self.refs.setdefault((category, name), set()).add(source)

    def command(self, code, params, source):
        if code in COMMAND_AUDIO and params:
            self.add(COMMAND_AUDIO[code], audio_name(params[0]), source)
        elif code == 231 and len(params) > 1:
            self.add('Graphics/Pictures', params[1], source)
        elif code == 222 and params:
            self.add('Graphics/Transitions', params[0], source)
        elif code == 131 and params:
            self.add('Graphics/Windowskins', params[0], source)
        elif code == 204 and len(params) > 1 and params[0] in (0, 1, 2):
            self.add(PANORAMA_FOG_BATTLEBACK[params[0]], params[1], source)
        elif code == 322 and len(params) > 3:
            self.add('Graphics/Characters', params[1], source)
            self.add('Graphics/Battlers', params[3], source)

    def walk(self, value, source):
        if isinstance(value, (Obj, list, dict)):
            if id(value) in self.seen:
                return
            self.seen.add(id(value))
        if isinstance(value, list):
            for item in value:
                self.walk(item, source)
        elif isinstance(value, dict) and not isinstance(value, Obj):
            for item in value.values():
                self.walk(item, source)
        elif isinstance(value, Obj):
            if value.cls == 'RPG::EventCommand':
                self.command(value.get('@code'), value.get('@parameters') or [], source)
            elif value.cls == 'RPG::MoveCommand':
                params = value.get('@parameters') or []
                if value.get('@code') == 41 and params:
                    self.add('Graphics/Characters', params[0], source)
                elif value.get('@code') == 44 and params:
                    self.add('Audio/SE', audio_name(params[0]), source)
            for key, item in value.items():
                if key in IVAR_GRAPHICS:
                    for name in (item if isinstance(item, list) else [item]):
                        self.add(IVAR_GRAPHICS[key], name, source)
                elif key in IVAR_AUDIO or (key.endswith('_se') or key == '@se'):
                    self.add(IVAR_AUDIO.get(key, 'Audio/SE'), audio_name(item), source)
                self.walk(item, source)


def index_folder(root):
    found = {}
    if root is None:
        return found
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'SYMLINK_REFUSED')
        if path.is_file():
            rel = path.relative_to(root)
            if len(rel.parts) >= 3:
                category = '/'.join(rel.parts[:2]).lower()
                stem = '/'.join(rel.parts[2:]).lower()
                key = (category, stem.rsplit('.', 1)[0] if '.' in rel.parts[-1] else stem)
                found.setdefault(key, []).append(rel.as_posix())
    return found


def resolve(category, name, index):
    exts = GRAPHIC_EXT if category.startswith('Graphics/') else AUDIO_EXT
    lowered = name.replace('\\', '/').lower()
    for key in ((category.lower(), lowered),
                (category.lower(), lowered.rsplit('.', 1)[0]) if lowered.endswith(exts) else None):
        if key and key in index:
            candidates = [p for p in index[key] if p.lower().endswith(exts)]
            if candidates:
                return sorted(candidates)[0]
    return None


def scan_scripts(path):
    scripts = Marshal(path.read_bytes()).load()
    require(isinstance(scripts, list), 'SCRIPTS_NOT_ARRAY')
    flags = {k: 0 for k in SCRIPT_FLAGS}
    win32, literals, total = set(), [], 0
    for entry in scripts:
        require(isinstance(entry, list) and len(entry) == 3, 'SCRIPT_ENTRY')
        code = zlib.decompress(entry[2])
        total += len(code)
        for key, pattern in SCRIPT_FLAGS.items():
            flags[key] += len(pattern.findall(code))
        win32.update((d.decode(), f.decode()) for d, f in WIN32API_CALL.findall(code))
        for kind, name in CACHE_LITERAL.findall(code):
            if kind.decode() in CACHE_DIRS:
                literals.append(('Graphics/' + CACHE_DIRS[kind.decode()], name))
        for _, folder, name in AUDIO_LITERAL.findall(code):
            literals.append(('Audio/' + folder.decode(), name))
    return {'count': len(scripts), 'source_bytes': total, 'flags': flags,
            'win32api_calls': sorted('%s:%s' % pair for pair in win32)}, literals


def inventory(game, rtps=()):
    game = game.resolve(strict=True)
    data = game / 'Data'
    require(data.is_dir() and (data / 'Scripts.rxdata').is_file(), 'RXDATA_PROJECT_REQUIRED')
    require(not list(game.glob('*.rgssad')), 'ENCRYPTED_ARCHIVE_UNSUPPORTED')
    collector = Collector()
    files = sorted(p for p in data.glob('*.rxdata') if p.name != 'Scripts.rxdata')
    for path in files:
        # id()-based cycle guard is only valid while this file's objects are alive.
        collector.seen = set()
        collector.walk(Marshal(path.read_bytes()).load(), path.name)
    scripts, literals = scan_scripts(data / 'Scripts.rxdata')
    for category, name in literals:
        collector.add(category, name, 'Scripts.rxdata')
    game_index = index_folder(game)
    rtp_indexes = [index_folder(Path(r).resolve(strict=True)) for r in rtps]
    rows, summary, extensions = [], {'game': 0, 'rtp': 0, 'missing': 0, 'case_mismatch': 0}, {}
    for (category, name), sources in sorted(collector.refs.items()):
        hit = resolve(category, name, game_index)
        origin = 'game' if hit else None
        for rtp_index in rtp_indexes:
            if hit is None:
                hit = resolve(category, name, rtp_index)
                origin = 'rtp' if hit else None
        origin = origin or 'missing'
        summary[origin] += 1
        if hit:
            ext = Path(hit).suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1
        exact = hit is None or Path(hit).name.startswith(name) or Path(hit).name == name
        summary['case_mismatch'] += 0 if exact else 1
        rows.append({'category': category, 'name': name, 'origin': origin, 'file': hit,
                     'case_exact': exact, 'sources': sorted(sources)[:5]})
    by_category = {}
    for row in rows:
        counts = by_category.setdefault(row['category'], {'game': 0, 'rtp': 0, 'missing': 0})
        counts[row['origin']] += 1
    return {'schema': 1, 'data_files': len(files), 'references': len(rows),
            'resolved': summary, 'by_category': by_category,
            'resolved_extensions': dict(sorted(extensions.items())), 'scripts': scripts,
            'rtp_required': summary['rtp'] > 0, 'rows': rows}


def tree_digest(root):
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        h.update(path.relative_to(root).as_posix().encode() + b'\0')
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--rtp', type=Path, action='append', default=[])
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    require(not args.report.exists(), 'FRESH_REPORT_REQUIRED')
    report = inventory(args.game, args.rtp)
    report['game_tree_sha256'] = tree_digest(args.game.resolve())
    report['rtp_tree_sha256'] = [tree_digest(Path(r).resolve()) for r in args.rtp]
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
