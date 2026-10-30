#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Instrument only a separate copy of the pinned 37a04d1 engine source.

Checks every input before editing. Does not build, download or deploy anything.
"""
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    'src/display/gl/gl-util.h': 'becedf9afe9104f0917e62a060020dd0aa60a0d0dd9ef5f8db1a37c97142013b',
    'src/display/gl/texpool.cpp': '20abc660b327260abcbdcd5ec3b6517996dac53096642cdfc9fd1c2e0194156e',
    'src/display/bitmap.cpp': '7b3a02fc83f24dc036d8f65c3579903098c27d12f04981587eb10d2bce326043',
}


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Unexpected instrumentation anchor')
    return text.replace(before, after, 1)


def instrument(source):
    source = Path(source)
    texts = {}
    for name, checksum in INPUTS.items():
        path = source / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError('Unexpected source: ' + name)
        texts[name] = path.read_text()
    header = source / 'src/display/gl/nextui-graphics-diagnostics.hpp'
    if header.exists():
        raise ValueError('Diagnostic header already exists')
    key = 'src/display/gl/gl-util.h'
    text = texts[key]
    text = replace_once(text, '#include "gl-fun.h"', '#include "gl-fun.h"\n#include "nextui-graphics-diagnostics.hpp"')
    for anchor, extra in (
        ('gl.GenTextures(1, &id.gl);', 'NextUIGraphics::gen(id.gl);'),
        ('gl.DeleteTextures(1, &id.gl);', 'NextUIGraphics::erase(id.gl);'),
        ('gl.BindTexture(GL_TEXTURE_2D, id.gl);', 'NextUIGraphics::bind(id.gl);'),
        ('gl.TexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, format, GL_UNSIGNED_BYTE, data);',
         'NextUIGraphics::image(width, height, true);'),
        ('gl.TexSubImage2D(GL_TEXTURE_2D, 0, x, y, width, height, format, GL_UNSIGNED_BYTE, data);',
         'NextUIGraphics::subimage(width, height);'),
        ('gl.TexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, 0);',
         'NextUIGraphics::image(width, height, false);'),
    ):
        text = replace_once(text, anchor, anchor + '\n\t\t' + extra)
    texts[key] = text
    key = 'src/display/gl/texpool.cpp'
    text = texts[key]
    for anchor in ('p->memSize -= byteCount(size);\n\t\t--p->objCount;', '++p->objCount;'):
        text = replace_once(text, anchor, anchor + '\n\tNextUIGraphics::pool(p->memSize, p->objCount);')
    texts[key] = text
    key = 'src/display/bitmap.cpp'
    texts[key] = replace_once(texts[key],
                             '    guardDisposed();\n\n    if (source.isDisposed())',
                             '    guardDisposed();\n    NextUIGraphics::blit();\n\n    if (source.isDisposed())')
    # All checksum and anchor checks completed before any write.
    header.write_bytes((ROOT / 'native/graphics_diagnostics.hpp').read_bytes())
    for name, text in texts.items():
        (source / name).write_text(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-copy', type=Path, required=True)
    instrument(parser.parse_args().source_copy)
