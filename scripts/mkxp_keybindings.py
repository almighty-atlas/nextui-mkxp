#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Write an mkxp-z keybindings.mkxp<N> file from a reviewed JSON mapping.

Mirrors mkxp-z src/input/keybindings.{h,cpp} FORMAT_VER 3: a 12-byte header
(format, RGSS version, count) followed by 16-byte BindingDesc records
(source type, union payload of two 32-bit words, target button), little-endian
as on AArch64. mkxp-z rejects the whole file if any record fails validation
and then falls back to its defaults, so we validate the same constraints here.
"""
import argparse
import json
from pathlib import Path
import struct

FORMAT_VER = 3
SOURCE_TYPES = {'button': 2, 'axis': 3}
# SDL_GameControllerButton / SDL_GameControllerAxis (SDL 2.x).
BUTTONS = {'A': 0, 'B': 1, 'X': 2, 'Y': 3, 'BACK': 4, 'GUIDE': 5, 'START': 6,
           'LEFTSTICK': 7, 'RIGHTSTICK': 8, 'LEFTSHOULDER': 9, 'RIGHTSHOULDER': 10,
           'DPAD_UP': 11, 'DPAD_DOWN': 12, 'DPAD_LEFT': 13, 'DPAD_RIGHT': 14}
AXES = {'LEFTX': 0, 'LEFTY': 1, 'RIGHTX': 2, 'RIGHTY': 3, 'TRIGGERLEFT': 4, 'TRIGGERRIGHT': 5}
DIRECTIONS = {'negative': 0, 'positive': 1}
# Input::ButtonCode values accepted by mkxp-z verifyDesc().
TARGETS = {'Down': 2, 'Left': 4, 'Right': 6, 'Up': 8, 'A': 11, 'B': 12, 'C': 13,
           'X': 14, 'Y': 15, 'Z': 16, 'L': 17, 'R': 18, 'Shift': 21, 'Ctrl': 22,
           'Alt': 23, 'F5': 25, 'F6': 26, 'F7': 27, 'F8': 28, 'F9': 29}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encode(mapping):
    require(mapping.get('format') == FORMAT_VER, 'FORMAT_VERSION')
    rgss = mapping.get('rgss_version')
    require(rgss in (1, 2, 3), 'RGSS_VERSION')
    records, seen = [], set()
    for item in mapping['bindings']:
        kind, target = item['type'], item['target']
        require(kind in SOURCE_TYPES, 'SOURCE_TYPE')
        require(target in TARGETS, 'TARGET')
        if kind == 'button':
            require(item['source'] in BUTTONS, 'BUTTON')
            payload = (BUTTONS[item['source']], 0)
        else:
            require(item['source'] in AXES and item['direction'] in DIRECTIONS, 'AXIS')
            payload = (AXES[item['source']], DIRECTIONS[item['direction']])
        key = (kind, payload)
        require(key not in seen, 'DUPLICATE_SOURCE')
        seen.add(key)
        records.append(struct.pack('<IIII', SOURCE_TYPES[kind], *payload, TARGETS[target]))
    require(0 < len(records) <= 1024, 'RECORD_COUNT')
    return struct.pack('<III', FORMAT_VER, rgss, len(records)) + b''.join(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mapping', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), 'FRESH_OUTPUT_REQUIRED')
    args.output.write_bytes(encode(json.loads(args.mapping.read_text())))


if __name__ == '__main__':
    main()
