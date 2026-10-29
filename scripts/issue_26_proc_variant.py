#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate a private experimental SDL-proc variant of the pinned MIT triangle.

The original input is never modified. No library is built or loaded here.
"""
import argparse
import hashlib
from pathlib import Path
import re

ORIGINAL_SHA256 = '8a08fe77d8675eb93368c15bd5fd3ddc1b00d9dd9229b8eda595e0a0e1432c42'


def generate(source):
    if hashlib.sha256(source.encode()).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('original PR23 source identity mismatch')
    names = sorted(set(re.findall(r'\b(gl[A-Z]\w+)\s*\(', source)))
    if len(names) != 26:
        raise ValueError('unexpected GL source surface')
    declarations = '\n'.join('static PFN' + n.upper() + 'PROC p_' + n + ';' for n in names)
    result = source.replace('#include <EGL/egl.h>\n', '').replace('    EGLDisplay display;\n', '')
    start = result.index('    display=eglGetCurrentDisplay();')
    end = result.index('    /* Vsync', start)
    result = result[:start] + result[end:]
    for name in names:
        result = re.sub(r'\b' + name + r'\s*\(', 'p_' + name + '(', result)
    result = result.replace('static volatile sig_atomic_t stopping;', declarations + '\nstatic volatile sig_atomic_t stopping;')
    lookups = '\n'.join(
        '    p_' + n + '=(PFN' + n.upper() + 'PROC)SDL_GL_GetProcAddress("' + n + '");\n'
        '    if (!p_' + n + ') { rc=32; stage("gl_proc_missing",rc); goto done; }'
        for n in names)
    anchor = '    stage("context_ready",0);'
    profile = ('\n    { int profile=0;\n'
               '      if (SDL_GL_GetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,&profile) ||\n'
               '          profile!=SDL_GL_CONTEXT_PROFILE_ES) { rc=33; stage("gles_profile",rc); goto done; }\n'
               '    }\n')
    result = result.replace(anchor, anchor + '\n' + lookups + profile)
    return '/* Experimental Issue 26 derivative; original PR23 source remains unchanged. */\n' + result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.original.read_bytes().decode('utf-8'))
    with args.output.open('x') as output:
        output.write(result)


if __name__ == '__main__':
    main()
