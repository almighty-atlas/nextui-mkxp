#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded data-only script inventory for private unpacked RMXP games.

Never executes Ruby/Marshal objects or exports game source/assets. RGSSAD v1
support reads its index and the one script table in memory; all output is
counts/identifiers, not source lines. Protocol reference: mkxp-z 37a04d1
src/crypto/rgssad.cpp (GPL-2.0-or-later); original implementation, no copied code.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import zlib

from rgss_inventory import Marshal

MAX_ARCHIVE = 2 * 1024**3
MAX_ENTRIES = 100000
MAX_SCRIPT = 8 * 1024**2
MAX_TOTAL = 64 * 1024**2
FLAGS = {
    'win32api': rb'\bWin32API\b', 'socket': rb'\brequire\s*[\x22\x27]socket[\x22\x27]',
    'http': rb'\b(?:HTTPLite|HTTP)\b', 'discord': rb'\brequire\s*[\x22\x27]discord[\x22\x27]',
    'flash': rb'\b(?:RMFlash|Flash\.ocx)\b', 'external_gif': rb'gif\.dll',
    'system_or_spawn': rb'\b(?:system|exec|spawn)\s*\(|`',
}


def require(value, code):
    if not value:
        raise ValueError(code)


def scripts_from_rgss1(path, include_roots=False):
    """Validate v1 index bounds, then decode only Data/Scripts.rxdata in memory."""
    require(path.is_file() and not path.is_symlink(), 'REGULAR_RGSS1_REQUIRED')
    length = path.stat().st_size
    require(8 <= length <= MAX_ARCHIVE, 'RGSS1_SIZE')
    key, count, selected, names = 0xDEADCAFE, 0, None, set()
    with path.open('rb') as stream:
        require(stream.read(8) == b'RGSSAD\0\x01', 'RGSS1_HEADER')

        def advance():
            nonlocal key
            value, key = key, (key * 7 + 3) & 0xffffffff
            return value

        def word():
            data = stream.read(4)
            require(len(data) == 4, 'RGSS1_TRUNCATED')
            return struct.unpack('<I', data)[0]

        while stream.tell() < length:
            count += 1
            require(count <= MAX_ENTRIES, 'RGSS1_ENTRIES')
            size = word() ^ advance()
            # The current native archiver has a 512-byte name buffer: refuse
            # malformed inputs rather than feeding an oversized name to it.
            require(0 < size < 512 and stream.tell() + size + 4 <= length, 'RGSS1_NAME_SIZE')
            raw = stream.read(size)
            decoded = bytes(c ^ (advance() & 255) for c in raw).replace(b'\\', b'/')
            require(not any(c < 32 or c == 127 for c in decoded), 'RGSS1_PATH')
            name = decoded.decode('utf-8', 'surrogateescape')
            pure = PurePosixPath(name)
            require(not pure.is_absolute() and '..' not in pure.parts and pure.as_posix() == name,
                    'RGSS1_PATH')
            require(name.casefold() not in names, 'RGSS1_DUPLICATE')
            names.add(name.casefold())
            size = word() ^ advance()
            offset = stream.tell()
            require(offset + size <= length, 'RGSS1_DATA_BOUNDS')
            if name.casefold() == 'data/scripts.rxdata':
                require(size <= MAX_SCRIPT, 'SCRIPT_TABLE_SIZE')
                selected = offset, size, key
            stream.seek(offset + size)
        require(selected is not None, 'SCRIPT_TABLE_MISSING')
        offset, size, data_key = selected
        stream.seek(offset)
        raw = stream.read(size)
    decoded = bytearray()
    for offset in range(0, len(raw), 4):
        chunk = raw[offset:offset + 4]
        value = int.from_bytes(chunk, 'little') ^ data_key
        decoded.extend(value.to_bytes(4, 'little')[:len(chunk)])
        data_key = (data_key * 7 + 3) & 0xffffffff
    result = bytes(decoded), count
    return (*result, sorted({name.split('/')[0] for name in names})) if include_roots else result


def inflate(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_SCRIPT, 'COMPRESSED_SCRIPT_SIZE')
    parser = zlib.decompressobj()
    result = parser.decompress(raw, MAX_SCRIPT + 1)
    require(len(result) <= MAX_SCRIPT and parser.eof and not parser.unused_data, 'SCRIPT_INFLATE_LIMIT')
    return result


def audit(game):
    game = Path(game)
    require(game.is_dir() and not game.is_symlink(), 'GAME_DIRECTORY')
    packed = game / 'Game.rgssad'
    table = game / 'Data/Scripts.rxdata'
    if packed.exists():
        raw, archive_entries, packed_roots = scripts_from_rgss1(packed, include_roots=True)
        layout = 'RGSSAD_V1'
    else:
        require(table.is_file() and not table.is_symlink() and table.stat().st_size <= MAX_SCRIPT,
                'SCRIPT_TABLE_REQUIRED')
        raw, archive_entries, layout, packed_roots = table.read_bytes(), None, 'LOOSE_RXDATA', []
    entries = Marshal(raw).load()
    require(isinstance(entries, list), 'SCRIPT_TABLE_ARRAY')
    counts = {key: 0 for key in FLAGS}
    constants, APIs = set(), {'Input': set(), 'Graphics': set(), 'System': set()}
    total, number = 0, 0

    def scan(code):
        nonlocal total, number
        total += len(code)
        number += 1
        require(total <= MAX_TOTAL and number <= MAX_ENTRIES, 'SOURCE_SCAN_LIMIT')
        for key, pattern in FLAGS.items():
            counts[key] += len(re.findall(pattern, code))
        constants.update(x.decode('ascii') for x in re.findall(rb'\bInput::([A-Z][A-Z_0-9]*)', code))
        for namespace in APIs:
            APIs[namespace].update(x.decode('ascii') for x in re.findall(
                rb'\b' + namespace.encode() + rb'\.([A-Za-z_]\w*[!?]?)', code))

    for entry in entries:
        require(isinstance(entry, list) and len(entry) == 3, 'SCRIPT_ENTRY')
        scan(inflate(entry[2]))
    loose = 0
    scripts = game / 'Scripts'
    require(not scripts.is_symlink(), 'SCRIPT_DIRECTORY_LINK')
    for path in sorted(scripts.rglob('*.rb')):
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_SCRIPT,
                'LOOSE_SCRIPT_FILE')
        require(not any(p.is_symlink() for p in path.parents), 'SCRIPT_PARENT_LINK')
        scan(path.read_bytes())
        loose += 1
    return {'schema': 1, 'layout': layout, 'packed_entries': archive_entries,
            'packed_roots': packed_roots,
            'table_entries': len(entries), 'loose_ruby_files': loose, 'source_bytes': total,
            'script_table_sha256': hashlib.sha256(raw).hexdigest(), 'flags': counts,
            'input_constants_referenced': sorted(constants),
            'api_names_referenced': {key: sorted(value) for key, value in APIs.items()},
            'api_scan_limit': 'Identifiers may occur in comments/conditional code or Ruby-defined wrappers; not a complete call graph',
            'ruby_executed': False, 'h700_result': 'NOT_TESTED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.game)
        require(not args.report.exists() and not args.report.is_symlink(), 'REPORT_EXISTS')
        require(not args.report.resolve().is_relative_to(Path(__file__).resolve().parents[1]),
                'PRIVATE_REPORT_REQUIRED')
        with args.report.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    except (ValueError, OSError, zlib.error):
        print(json.dumps({'status': 'FANGAME_AUDIT_BLOCKED'}))
        return 2
    print(json.dumps({'status': 'FANGAME_AUDIT_PASS', 'ruby_executed': False,
                      'layout': result['layout'], 'table_entries': result['table_entries'],
                      'loose_ruby_files': result['loose_ruby_files'], 'flags': result['flags']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
