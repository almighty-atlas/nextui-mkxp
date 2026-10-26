#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private patched Mali SDL source build and proc-variant link. No target runs."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import issue_26_sandbox as gate
from issue_26_proc_variant import generate


def inspect_exports(text, required):
    sonames = re.findall(r'\(SONAME\).*?\[([^]]+)\]', text)
    exports = set()
    for line in text.splitlines():
        fields = line.split()
        if (len(fields) >= 8 and fields[4] in ('GLOBAL', 'WEAK') and
                fields[5] == 'DEFAULT' and fields[6] != 'UND'):
            exports.add(fields[7].split('@')[0])
    if sonames != ['libSDL2-2.0.so.0'] or set(required)-exports:
        raise ValueError('SDL SONAME/export contract mismatch')
    return sorted(set(required))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'compiler', 'compiler-archive', 'records', 'sysroot', 'sdl', 'patch', 'api', 'triangle'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--sysroot-tree-sha256', required=True)
    parser.add_argument('--lock', type=Path, default=Path(__file__).resolve().parents[1]/'docs/build/issue-26-inputs.json')
    a = parser.parse_args()
    for name, value in vars(a).items():
        if isinstance(value, Path): setattr(a, name, value.resolve())
    lock = json.loads(a.lock.read_text()); work = a.workspace
    if work.exists(): raise ValueError('workspace must be fresh')
    gate.verify_archive_tree(a.compiler_archive, lock['compiler']['sha256'], a.compiler)
    if gate.tree_digest(a.sysroot) != a.sysroot_tree_sha256: raise ValueError('sysroot provenance mismatch')
    if gate.tree_digest(a.sdl) != lock['sdl']['tree_sha256']: raise ValueError('SDL source mismatch')
    gate.check_file(a.patch, lock['sdl']['recipe_patch_sha256'], [a.patch.parent])
    gate.check_file(a.triangle, lock['triangle']['sha256'], [a.triangle.parent])
    for header in lock['khronos']: gate.check_file(a.api/header['path'], header['sha256'], [a.api])
    records = json.loads(a.records.read_text()); work.mkdir(parents=True)
    gate.farm(work/'tools', records)
    cc = a.compiler/'x86_64-aarch64-nextui-linux-gnu/bin/aarch64-nextui-linux-gnu-gcc'
    gcc = cc.parents[1]/'lib/gcc/aarch64-nextui-linux-gnu/8.3.0'
    libs = a.sysroot/'usr/lib64'
    flags = ['--sysroot='+str(a.sysroot), '-B'+str(libs)+'/', '-static-libgcc', '-nostdinc',
             '-isystem', str(gcc/'include'), '-isystem', str(gcc/'include-fixed'),
             '-isystem', str(a.sysroot/'usr/include'), '-L'+str(a.sysroot/'lib64'),
             '-L'+str(libs), '-Wl,-rpath-link,'+str(a.sysroot/'lib64')]
    (work/'empty-pkgconfig').mkdir()
    env = gate.environment(work, work/'tools', {'CC':str(cc), 'BUILD_CC':'/usr/bin/gcc',
        'PKG_CONFIG_LIBDIR':str(work/'empty-pkgconfig'), 'PKG_CONFIG_SYSROOT_DIR':str(a.sysroot)})
    def run(label, argv, cwd=work):
        result = gate.checked_run(argv, cwd, env, records, work/'logs', label)
        print(label, result['exit_code'], flush=True)
        if result['exit_code']: raise ValueError('stage failed: '+label)
    source = work/'sdl-source'; shutil.copytree(a.sdl, source, ignore=shutil.ignore_patterns('.git'))
    run('h700-patch', [records['patch']['path'], '-p1', '--input='+str(a.patch)], source)
    patched_digest = gate.tree_digest(source)
    build = work/'sdl-build'; build.mkdir()
    # Video/timer experiment. Audio is explicitly disabled rather than silently
    # pretending to reproduce the shipped ALSA configuration without its headers.
    configure = ['/usr/bin/sh', source/'configure', '--build=x86_64-pc-linux-gnu',
        '--host=aarch64-nextui-linux-gnu', '--prefix=/usr', '--enable-video-mali',
        '--enable-video-opengles', '--disable-video-opengl', '--disable-video-x11',
        '--disable-video-wayland', '--disable-video-kmsdrm', '--disable-audio',
        '--disable-dbus', '--disable-ibus', '--disable-fcitx', '--disable-hidapi',
        '--disable-libudev', '--disable-power', '--disable-sensor', '--disable-locale',
        '--enable-filesystem', '--enable-loadso', '--enable-shared', '--disable-static',
        'CFLAGS='+' '.join(flags), 'CPPFLAGS=-I'+str(a.api),
        'LDFLAGS='+' '.join(flags)+' -Wl,-z,defs -Wl,-Map='+str(work/'sdl.map')]
    run('sdl-configure', configure, build)
    config = build/'include/SDL_config.h'
    if '#define SDL_VIDEO_DRIVER_MALI 1' not in config.read_text(): raise ValueError('Mali backend disabled')
    # Libtool otherwise deletes its generated INPUT(...) script after linking.
    # Retain those actual bytes so every LOAD record remains inspectable.
    libtool = build/'libtool'; text = libtool.read_text(); before = gate.sha256(libtool)
    start = text.index('output=$output_objdir/$output_la.lnkscript')
    position = text.index('func_append delfiles " $output"', start)
    text = text[:position] + text[position:].replace('func_append delfiles " $output"',
        ': # Issue 26: retain actual linker input script for provenance inspection', 1)
    libtool.write_text(text)
    (work/'libtool-retention.json').write_text(json.dumps({'before_sha256':before,
        'after_sha256':gate.sha256(libtool), 'change':'omit cleanup registration for GNU ld INPUT script only'}, indent=2)+'\n')
    # Libtool filters bare -B and -static-libgcc. Its documented -Wc escape
    # preserves these compiler-driver flags during the shared-library link.
    link_flags = ' '.join(flags)+' -Wl,-z,defs -Wl,-Map='+str(work/'sdl.map')
    link_flags += ' -Wc,-B'+str(libs)+'/,-static-libgcc'
    run('sdl-make', [records['make']['path'], '-j2', 'LDFLAGS='+link_flags], build)
    library = (build/'build/.libs/libSDL2.so').resolve(strict=True)
    # Audit all actual SDL link LOAD inputs, including resolved symlinks.
    loaded = [str(Path(p) if Path(p).is_absolute() else build/p)
              for p in re.findall(r'^LOAD (.+)$', (work/'sdl.map').read_text(), re.M)]
    gate.validate_search_paths(loaded, [work, a.sysroot, cc.parents[1]])
    old = cc.parents[1]/'aarch64-nextui-linux-gnu/libc'
    if any(Path(p).resolve().is_relative_to(old) for p in loaded): raise ValueError('old libc in SDL link')
    includes = work/'include'; shutil.copytree(source/'include', includes/'SDL2')
    shutil.copy2(config, includes/'SDL2/SDL_config.h')
    variant = work/'triangle-proc.c'; variant.write_text(generate(a.triangle.read_text()))
    run('variant-object', [cc, *flags, '-I'+str(includes), '-I'+str(a.api), '-std=c99',
        '-O2', '-Wall', '-Wextra', '-Werror', '-MD', '-MF', work/'variant.d',
        '-c', variant, '-o', work/'variant.o'])
    import shlex
    dependencies = shlex.split((work/'variant.d').read_text().replace('\\\n',' '))[1:]
    gate.validate_search_paths(dependencies, [work, a.sysroot, a.api, gcc])
    run('variant-link', [cc, *flags, work/'variant.o', '-L'+str(library.parent),
        '-Wl,-rpath-link,'+str(library.parent), '-Wl,-Map='+str(work/'variant.map'),
        '-lSDL2', '-o', work/'triangle-proc'])
    facts = gate.elf_facts(work/'triangle-proc', records['readelf']['path'], env, records)
    errors = gate.policy_errors(facts, '4.9', '2.28', ['libSDL2-2.0.so.0', 'libc.so.6'])
    if errors: raise ValueError(str(errors))
    if facts['needed'] != ['libSDL2-2.0.so.0', 'libc.so.6']: raise ValueError('unexpected video link surface')
    link_inputs = re.findall(r'^LOAD (.+)$', (work/'variant.map').read_text(), re.M)
    gate.validate_search_paths(link_inputs, [work, a.sysroot, cc.parents[1]])
    if any(Path(p).resolve().is_relative_to(old) for p in link_inputs): raise ValueError('old libc in variant link')
    sdl_facts = gate.elf_facts(library, records['readelf']['path'], env, records)
    run('sdl-symbols', [records['readelf']['path'], '--wide', '--dynamic', '--dyn-syms', library])
    required = set(re.findall(r'\b(SDL_\w+)\s*\(', variant.read_text()))-{'SDL_VERSION'}
    exports = inspect_exports((work/'logs/sdl-symbols.log').read_text(), required)
    sdl_facts['soname'] = 'libSDL2-2.0.so.0'  # Verified by inspect_exports above.
    if (sdl_facts['machine'] != 183 or sdl_facts['type'] != 3 or sdl_facts['rpaths'] or
            set(sdl_facts['needed']) != {'libc.so.6','libm.so.6','libdl.so.2','libpthread.so.0'} or
            any(v not in ('GLIBC_2.17','GLIBC_2.27') for v in sdl_facts['required_versions'])):
        raise ValueError('SDL dependency/version contract mismatch')
    run('variant-link-repeat', [cc, *flags, work/'variant.o', '-L'+str(library.parent),
        '-Wl,-rpath-link,'+str(library.parent), '-Wl,-Map='+str(work/'variant-repeat.map'),
        '-lSDL2', '-o', work/'triangle-proc-repeat'])
    if gate.sha256(work/'triangle-proc-repeat') != facts['sha256']:
        raise ValueError('same-workspace variant repeat link differs')
    result = {'status':'SDL_ONLY_HOST_LINKED', 'variant_sha256':gate.sha256(variant),
        'original_sha256':gate.sha256(a.triangle), 'patched_source_tree':patched_digest,
        'sysroot_tree':a.sysroot_tree_sha256, 'variant':facts, 'sdl':sdl_facts,
        'library_private_path':str(library), 'verified_sdl_exports':exports,
        'same_workspace_repeat_link_identical':True, 'sdl_load_inputs':loaded,
        'variant_load_inputs':link_inputs, 'dependencies':dependencies,
        'h700_runtime':'NOT_TESTED', 'distribution':'BLOCKED'}
    (work/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr); raise SystemExit(1)
