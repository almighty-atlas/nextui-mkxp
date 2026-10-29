#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private pinned source preparation and guarded Pak assembly. Never runs ARM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import struct
import subprocess

REPO = Path(__file__).resolve().parents[2]
PR23 = '60721c1a81a9f54e507650f313a479ecaa9b6d2a'
PR27 = '1c04c578e3a35acc40b8669986228e3a2ae056c0'
ORIGINAL = '8a08fe77d8675eb93368c15bd5fd3ddc1b00d9dd9229b8eda595e0a0e1432c42'
VARIANT = '9b95b0bf6cddfebb6f2946b39896b69fea61614157b80ccc52d698d81e48f19d'
SDL_HASH = '76de58c80f9a6d901fc5563711b9edc869a759c9446c5a6cd798f4c6774f7577'
PAK = 'Tools/h700/RMXP-Video-Test.pak'
ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C'}
SDL_IMPORTS = set('''SDL_ClearError SDL_CreateWindow SDL_Delay SDL_DestroyWindow
SDL_GL_CreateContext SDL_GL_DeleteContext SDL_GL_GetAttribute SDL_GL_GetDrawableSize
SDL_GL_GetProcAddress SDL_GL_MakeCurrent SDL_GL_SetAttribute SDL_GL_SetSwapInterval
SDL_GL_SwapWindow SDL_GetCurrentVideoDriver SDL_GetError SDL_GetTicks SDL_GetVersion
SDL_Init SDL_PollEvent SDL_Quit SDL_getenv'''.split())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(commit, path):
    return subprocess.run(['/usr/bin/git', '-C', str(REPO), 'show', commit+':'+path],
                          env=ENV, capture_output=True, check=True, timeout=30).stdout


def fresh(path):
    path = Path(path).absolute()
    if path.resolve().is_relative_to(REPO):
        raise ValueError('private outputs must be outside repository')
    path.mkdir(parents=True, exist_ok=False)
    path.chmod(0o700)
    return path


def prepare(destination):
    # Exact local git objects only; preparation never fetches or executes build code.
    original = blob(PR23, 'spikes/h700-video/triangle.c')
    if sha(original) != ORIGINAL:
        raise ValueError('original source identity mismatch')
    exports = {}
    for name in ('issue_26_proc_variant.py', 'issue_26_sandbox.py',
                 'issue_26_sysroot.py', 'issue_26_sdl_proc.py'):
        path = 'scripts/'+name
        exports[path] = blob(PR27, path)
    exports['docs/build/issue-26-inputs.json'] = blob(PR27, 'docs/build/issue-26-inputs.json')
    for path in ('LICENSE', 'Tools/h700/RMXP-Video-Test.pak/launch.sh',
                 'Tools/h700/RMXP-Video-Test.pak/SOURCE_ONLY'):
        exports[path] = blob(PR23, 'spikes/h700-video/'+path)
    # Preserve the existing original native mock suite; no SDL/Khronos header copy.
    fixture_paths = ('LICENSE', 'PROVENANCE.md', 'include/GLES2/gl2.h',
                     'include/SDL2/SDL.h', 'mock_proc.c', 'triangle-original.c')
    for path in fixture_paths:
        name = 'scripts/issue_26_tests/fixtures/'+path
        exports[name] = blob(PR27, name)
    name = 'scripts/issue_26_tests/test_proc.py'
    exports[name] = blob(PR27, name)
    work = fresh(destination)
    for path, data in exports.items():
        target = work/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    generated = runpy.run_path(str(work/'scripts/issue_26_proc_variant.py'))['generate'](original.decode())
    if sha(generated.encode()) != VARIANT:
        raise ValueError('generated 26-proc variant identity mismatch')
    (work/'triangle-original.c').write_bytes(original)
    (work/'triangle-proc.c').write_text(generated)
    (work/PAK/'launch.sh').chmod(0o755)
    provenance = {'status': 'SOURCE_PREPARED', 'meaning': 'pinned sources prepared, not compiled',
                  'pr23': PR23, 'pr27': PR27, 'original_sha256': ORIGINAL,
                  'variant_sha256': VARIANT, 'installed_sdl_owner_sha256': SDL_HASH,
                  'files': {p: sha(data) for p, data in sorted(exports.items())},
                  'h700_runtime': 'NOT_TESTED', 'distribution': 'BLOCKED'}
    (work/'preparation.json').write_text(json.dumps(provenance, indent=2)+'\n')
    return provenance


def parse_elf(header, text):
    if (len(header) < 20 or header[:7] != b'\x7fELF\x02\x01\x01'
            or struct.unpack_from('<HH', header, 16) != (2, 183)):
        raise ValueError('require ELF64 LE AArch64 ET_EXEC')
    interps = re.findall(r'Requesting program interpreter:\s*([^\]]+)', text)
    if interps != ['/lib/ld-linux-aarch64.so.1']:
        raise ValueError('interpreter mismatch')
    needed = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', text)
    if sorted(needed) != ['libSDL2-2.0.so.0', 'libc.so.6']:
        raise ValueError('unexpected NEEDED')
    if re.search(r'\((?:RPATH|RUNPATH|TEXTREL)\)', text):
        raise ValueError('runtime path or text relocation')
    notes = re.findall(r'OS: Linux, ABI: ([0-9.]+)', text)
    if notes != ['4.9.0']:
        raise ValueError('require reviewed Linux 4.9.0 ABI note')
    if not re.search(r'GNU_STACK\s+[^\n]*\sRW\s', text):
        raise ValueError('require non-executable stack')
    versions = set()
    in_needs = False
    for line in text.splitlines():
        if line.startswith('Version '):
            in_needs = line.startswith('Version needs section')
        if in_needs:
            versions.update(re.findall(r'Name:\s*(\S+)', line))
    if versions != {'GLIBC_2.17'}:
        raise ValueError('require only GLIBC_2.17 version needs')
    imports = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[0].endswith(':') and fields[6] == 'UND':
            if fields[4] not in ('GLOBAL', 'WEAK') or fields[5] != 'DEFAULT':
                raise ValueError('unexpected dynamic symbol visibility/binding')
            name = fields[7]
            if re.match(r'(?:gl[A-Z]|egl[A-Z])', name):
                raise ValueError('direct GL/EGL import')
            if name.startswith('SDL_'):
                if '@' in name or fields[3] not in ('FUNC', 'NOTYPE'):
                    raise ValueError('versioned or non-function SDL import')
            elif not (name.endswith('@GLIBC_2.17') or
                      (fields[4] == 'WEAK' and name in ('__gmon_start__', '_ITM_registerTMCloneTable',
                                                       '_ITM_deregisterTMCloneTable'))):
                raise ValueError('unreviewed dynamic import')
            imports.append(name)
    sdl = sorted(n for n in imports if n.startswith('SDL_'))
    if set(sdl) != SDL_IMPORTS or len(sdl) != 21:
        raise ValueError('21 SDL import contract mismatch')
    return {'machine': 'AArch64', 'type': 'ET_EXEC', 'interpreter': interps[0],
            'needed': sorted(needed), 'glibc_needs': sorted(versions),
            'gnu_linux_abi': '4.9.0', 'sdl_undefined': sdl,
            'undefined': sorted(imports), 'rpath': False, 'executable_stack': False}


def inspect(binary, readelf):
    if not readelf.is_absolute():
        raise ValueError('absolute trusted host readelf required')
    if binary.is_symlink() or not binary.is_file() or not 64 <= binary.stat().st_size <= 32*1024*1024:
        raise ValueError('bounded regular ELF required')
    data = binary.read_bytes()
    result = subprocess.run([str(readelf), '--wide', '-h', '-l', '-d', '--version-info',
                             '--notes', '--dyn-syms', str(binary)], env=ENV,
                            capture_output=True, text=True, check=True, timeout=30)
    if result.stderr or len(result.stdout) > 4*1024*1024:
        raise ValueError('readelf warning or oversized output')
    facts = parse_elf(data[:20], result.stdout)
    if binary.read_bytes() != data:
        raise ValueError('binary changed during inspection')
    facts['sha256'] = sha(data)
    return facts


def assemble(prepared, build, destination, readelf):
    # Private output of the real PR27 source-build driver, not the installed DSO.
    receipt = json.loads((build/'result.json').read_text())
    variant = (prepared/'triangle-proc.c').read_bytes()
    if sha(variant) != VARIANT or (receipt.get('status') != 'SDL_ONLY_HOST_LINKED'
                                 or receipt.get('variant_sha256') != VARIANT
                                 or receipt.get('original_sha256') != ORIGINAL):
        raise ValueError('source/build receipt identity mismatch')
    facts = inspect(build/'triangle-proc', readelf)
    if receipt['variant']['sha256'] != facts['sha256']:
        raise ValueError('build receipt ELF hash mismatch')
    # Re-read original pinned shell/guard/license, not mutable prepared copies.
    contents = {
        PAK+'/launch.sh': blob(PR23, 'spikes/h700-video/Tools/h700/RMXP-Video-Test.pak/launch.sh'),
        PAK+'/SOURCE_ONLY': blob(PR23, 'spikes/h700-video/Tools/h700/RMXP-Video-Test.pak/SOURCE_ONLY'),
        PAK+'/LICENSE': blob(PR23, 'spikes/h700-video/LICENSE'),
        PAK+'/source/triangle-proc.c': variant,
        PAK+'/bin/triangle': (build/'triangle-proc').read_bytes(),
    }
    if sha(contents[PAK+'/bin/triangle']) != facts['sha256']:
        raise ValueError('binary changed before staging')
    output = fresh(destination)
    for path, data in contents.items():
        target = output/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if path.endswith(('/launch.sh', '/bin/triangle')) else 0o644)
    report = {'status': 'HOST_VERIFIED', 'elf': facts,
              'meaning': 'ELF metadata verified; guarded PRIVATE staging only',
              'files': {p: sha(v) for p, v in sorted(contents.items())},
              'installed_sdl_identity': 'OWNER_REPORTED', 'installed_sdl_sha256': SDL_HASH,
              'sdl_link_input': 'PR27 privately source-built SDL; NOT shipped',
              'source_only': True, 'h700_runtime': 'NOT_TESTED', 'distribution': 'BLOCKED'}
    (output/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('assemble')
    for name in ('prepared', 'build', 'output', 'readelf'):
        p.add_argument('--'+name, type=Path, required=True)
    a = parser.parse_args()
    os.umask(0o077)
    try:
        report = prepare(a.output) if a.command == 'prepare' else assemble(a.prepared, a.build, a.output, a.readelf)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError):
        print(json.dumps({'status': 'BUILD_BLOCKED', 'reason': 'input_or_host_gate_failed',
                          'h700_runtime': 'NOT_TESTED'}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
