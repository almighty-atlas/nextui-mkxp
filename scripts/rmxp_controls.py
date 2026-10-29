#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate and encode explicit per-game mkxp-z FORMAT_VER 3 controller mappings."""
import argparse
import json
import os
from pathlib import Path
import struct

BUTTONS = {'A': 0, 'B': 1, 'X': 2, 'Y': 3, 'BACK': 4, 'GUIDE': 5, 'START': 6,
           'LEFTSTICK': 7, 'RIGHTSTICK': 8, 'LEFTSHOULDER': 9, 'RIGHTSHOULDER': 10,
           'DPAD_UP': 11, 'DPAD_DOWN': 12, 'DPAD_LEFT': 13, 'DPAD_RIGHT': 14}
AXES = {'LEFTX': 0, 'LEFTY': 1, 'RIGHTX': 2, 'RIGHTY': 3, 'TRIGGERLEFT': 4, 'TRIGGERRIGHT': 5}
TARGETS = {'Down': 2, 'Left': 4, 'Right': 6, 'Up': 8, 'A': 11, 'B': 12, 'C': 13,
           'X': 14, 'Y': 15, 'Z': 16, 'L': 17, 'R': 18, 'Shift': 21, 'Ctrl': 22,
           'Alt': 23, 'F5': 25, 'F6': 26, 'F7': 27, 'F8': 28, 'F9': 29}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encode(mapping):
    require(isinstance(mapping, dict) and set(mapping) == {'format', 'rgss_version', 'bindings'}, 'SCHEMA')
    require(type(mapping['format']) is int and mapping['format'] == 3, 'FORMAT')
    require(type(mapping['rgss_version']) is int and mapping['rgss_version'] in (1, 2, 3), 'RGSS')
    require(isinstance(mapping['bindings'], list) and 0 < len(mapping['bindings']) <= 1024, 'BINDINGS')
    records, seen, targets = [], set(), set()
    for item in mapping['bindings']:
        require(isinstance(item, dict), 'BINDING')
        kind = item.get('type')
        require(kind in ('button', 'axis'), 'TYPE')
        require(set(item) == ({'type', 'source', 'target'} if kind == 'button' else
                             {'type', 'source', 'target', 'direction'}), 'BINDING_KEYS')
        require(isinstance(item['target'], str) and item['target'] in TARGETS, 'TARGET')
        sources = BUTTONS if kind == 'button' else AXES
        require(isinstance(item['source'], str) and item['source'] in sources, 'SOURCE')
        direction = 0
        if kind == 'axis':
            require(item['direction'] in ('negative', 'positive'), 'DIRECTION')
            direction = int(item['direction'] == 'positive')
        key = (2 if kind == 'button' else 3, sources[item['source']], direction)
        require(key not in seen, 'DUPLICATE_SOURCE')
        seen.add(key)
        targets.add(item['target'])
        records.append(struct.pack('<IIII', *key, TARGETS[item['target']]))
    require({'Up', 'Down', 'Left', 'Right', 'B', 'C'} <= targets, 'ESSENTIAL_CONTROLS_MISSING')
    return struct.pack('<III', 3, mapping['rgss_version'], len(records)) + b''.join(records)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mapping', type=Path)
    parser.add_argument('output', type=Path, help='Fresh output only; preserve existing per-game mappings manually')
    args = parser.parse_args()
    payload = encode(json.loads(args.mapping.read_text()))
    require(not any(p.is_symlink() for p in (args.output, *args.output.parents)), 'OUTPUT_SYMLINK')
    with args.output.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == '__main__':
    main()
