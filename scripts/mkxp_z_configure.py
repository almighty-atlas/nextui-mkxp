#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private, offline `meson setup` / `meson compile` of pinned mkxp-z for H700.

Setup verifies engine commit, wrap lock, packagecache, private Mali SDL and
the pinned compiler/sysroot/native Ruby, stages them in a FRESH private job
directory and runs Meson in a network-less, read-only container. Compile
reuses that configured job with the same inputs. Target binaries are never
run; all logs are scanned for target-execution attempts.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

from h700_ruby_batch import IMAGE, input_pins, require, sha
from mkxp_z_source_lock import lock

ROOT = Path(__file__).resolve().parents[1]
SDL_SHA256 = '25dba080d55738a60fe6a3c7a1ad0a0069fd41719eb437ce7902fad152eec6d0'
SDL_SONAME_FILE = 'libSDL2-2.0.so.0.2800.5'
GIB = 1024**3
TOOLS = '/build/toolchains/gcc-8.3/x86_64-aarch64-nextui-linux-gnu/bin/aarch64-nextui-linux-gnu-'
SYSROOT = '/build/sysroot-runs/sysroot-20261027-212308/sysroot'
BUILD_ALIAS = 'x86_64-pc-linux-gnu'
# Configure-time evidence that a target binary was started on the build host.
EXEC_ATTEMPT = re.compile(r'Exec format error|cannot execute binary file')


def option_value(value):
    return str(value).lower() if isinstance(value, bool) else str(value)


def cross_file():
    compiler = ["'" + TOOLS + 'gcc' + "'", "'--sysroot=" + SYSROOT + "'",
                "'-B" + SYSROOT + "/usr/lib64/'"]
    cxx = ["'" + TOOLS + 'g++' + "'"] + compiler[1:]
    lines = ['[binaries]',
             'c = [' + ', '.join(compiler) + ']',
             'cpp = [' + ', '.join(cxx) + ']']
    for tool in ('ar', 'ranlib', 'strip', 'nm', 'objcopy', 'readelf'):
        lines.append(tool + " = '" + TOOLS + tool + "'")
    lines += ["pkg-config = '/usr/bin/pkg-config'", "cmake = '/usr/bin/cmake'",
              "ruby = '/work/prefix/bin/ruby'", "bison = '/usr/bin/bison'",
              # No sys_root property: Meson would prefix it to the private SDL
              # pkg-config paths. The compiler already receives --sysroot.
              '', '[properties]', "pkg_config_libdir = ['/job/sdl-prefix/lib/pkgconfig']",
              '', '[host_machine]', "system = 'linux'", "cpu_family = 'aarch64'",
              "cpu = 'aarch64'", "endian = 'little'", '']
    return '\n'.join(lines)


def sdl_pc():
    return ('prefix=/job/sdl-prefix\nexec_prefix=${prefix}\nlibdir=${prefix}/lib\n'
            'includedir=${prefix}/include\n\nName: sdl2\n'
            'Description: Private pinned Mali-fbdev SDL2 (not a release artifact)\n'
            'Version: 2.28.5\nLibs: -L${libdir} -lSDL2\n'
            'Libs.private: -lm -ldl -lpthread\n'
            'Cflags: -I${includedir}/SDL2 -I${includedir} -D_REENTRANT\n')


def stage_sdl(run, prefix):
    receipt = json.loads((run / 'result.json').read_text())
    require(receipt['status'] == 'SDL_ONLY_HOST_LINKED' and
            receipt['sdl']['sha256'] == SDL_SHA256, 'SDL_RECEIPT')
    library = run / 'sdl-build/build/.libs' / SDL_SONAME_FILE
    require(sha(library) == SDL_SHA256, 'SDL_LIBRARY_HASH')
    headers = prefix / 'include/SDL2'
    headers.mkdir(parents=True)
    for path in sorted((run / 'sdl-source/include').glob('*.h')):
        require(not path.is_symlink(), 'SDL_HEADER_LINK')
        shutil.copyfile(path, headers / path.name)
    for name in ('SDL_config.h', 'SDL_revision.h'):
        shutil.copyfile(run / 'sdl-build/include' / name, headers / name)
    lib = prefix / 'lib'
    (lib / 'pkgconfig').mkdir(parents=True)
    shutil.copyfile(library, lib / SDL_SONAME_FILE)
    (lib / 'libSDL2-2.0.so.0').symlink_to(SDL_SONAME_FILE)
    (lib / 'libSDL2.so').symlink_to(SDL_SONAME_FILE)
    shutil.copyfile(run / 'sdl-build/build/.libs/libSDL2main.a', lib / 'libSDL2main.a')
    (lib / 'pkgconfig/sdl2.pc').write_text(sdl_pc())
    require(sha(lib / SDL_SONAME_FILE) == SDL_SHA256, 'SDL_COPY_HASH')


def apply_diffs(directory, packagefiles, diffs):
    """Meson skips diff_files for a pre-provided git checkout; apply the locked ones."""
    for name, expected in diffs.items():
        path = packagefiles / name
        require(sha(path) == expected, 'DIFF_FILE_HASH:' + name)
        run = subprocess.run(['patch', '-p1', '--batch', '--forward', '-i', str(path)],
                             cwd=directory, capture_output=True, text=True, timeout=120,
                             env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        require(run.returncode == 0, 'DIFF_APPLY_FAILED:' + name + ':' + run.stdout[-200:])


def add_local_patches(subprojects, profile):
    """Append reviewed, hash-pinned repository patches to the staged wraps."""
    applied = {}
    for wrap, patches in sorted(profile.get('local_patches', {}).items()):
        path = subprojects / (wrap + '.wrap')
        text = path.read_text()
        sentinel = '    end-of-diff-files.patch\n'
        require(text.count(sentinel) == 1, 'WRAP_SENTINEL:' + wrap)
        names = []
        for item in patches:
            source = ROOT / item['file']
            require(sha(source) == item['sha256'], 'LOCAL_PATCH_HASH:' + item['file'])
            name = 'nextui-' + source.name
            require(not (subprojects / 'packagefiles' / name).exists(), 'LOCAL_PATCH_COLLISION')
            shutil.copyfile(source, subprojects / 'packagefiles' / name)
            names.append(name)
            applied[item['file']] = item['sha256']
        path.write_text(text.replace(sentinel, ''.join('    ' + n + ',\n' for n in names) + sentinel))
    return applied


def setup_command(profile):
    args = ['meson', 'setup', '/job/build', '/job/src', '--cross-file', '/job/cross.ini',
            '--wrap-mode=nodownload', '--buildtype=release']
    for key, value in profile['meson_options'].items():
        args.append('-D' + key + '=' + option_value(value))
    return args


COMPILE_COMMAND = ['meson', 'compile', '-C', '/job/build', '-j', '2']


def docker_command(args, work, name, inner):
    mounts = [(args.native, '/work', True), (work, '/job', False),
              (args.toolchain, '/build/toolchains/gcc-8.3', True),
              (args.sysroot, SYSROOT, True)]
    cmd = ['docker', 'run', '--name', name, '--rm', '--pull=never', '--network=none',
           '--read-only', '--cpus=2', '--memory=4g', '--memory-swap=4g',
           '--cap-drop=ALL', '--security-opt=no-new-privileges',
           '--user=' + str(os.getuid()) + ':' + str(os.getgid()),
           '--tmpfs', '/tmp:rw,nosuid,nodev,size=512m', '--workdir=/job',
           '--env', 'HOME=/tmp', '--env', 'LC_ALL=C', '--env', 'TZ=UTC',
           '--env', 'PATH=/work/prefix/bin:/usr/bin:/bin',
           # Forces autoconf cross mode in every nested configure (see H700_RUBY_BATCH.md).
           '--env', 'build_alias=' + BUILD_ALIAS]
    for source, target, readonly in mounts:
        require(',' not in str(source), 'UNSUPPORTED_MOUNT_PATH')
        cmd += ['--mount', 'type=bind,src=' + str(source) + ',dst=' + target +
                (',readonly' if readonly else '')]
    return cmd + ['--entrypoint=' + inner[0], IMAGE] + inner[1:]


def tree_size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())


def guard(work, budget, reserve_gib, check_budget=True):
    # Owner-approved reserve (docs/MKXP_Z_SOURCE_LOCK.md); stop 1 GiB above it.
    require(shutil.disk_usage(work).free >= (reserve_gib + 1) * GIB,
            'FREE_SPACE_GUARD_' + str(reserve_gib + 1) + '_GIB')
    if check_budget:
        require(tree_size(work) <= budget, 'PRIVATE_JOB_BUDGET')


def exec_attempts(build):
    hits = []
    for path in sorted(build.rglob('*')):
        if path.is_file() and path.suffix in ('.log', '.txt') and path.stat().st_size < 64 * 1024**2:
            if EXEC_ATTEMPT.search(path.read_text(errors='replace')):
                hits.append(path.relative_to(build).as_posix())
    return hits


def run_container(args, work, inner, log_name, receipt):
    """One bounded container run; kills only its own uniquely named container."""
    name = 'nextui-mkxp-' + log_name + '-' + uuid.uuid4().hex[:12]
    cmd = docker_command(args, work, name, inner)
    receipt['docker_command'] = cmd
    started, process, last_budget = time.monotonic(), None, 0.0
    try:
        with (work / (log_name + '.log')).open('wb') as log:
            process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                       env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
            while process.poll() is None:
                now = time.monotonic()
                check = now - last_budget > 30
                last_budget = now if check else last_budget
                guard(work, args.budget_gib * GIB, args.reserve_gib, check)
                require(now - started < args.timeout, 'TIMEOUT_' + log_name.upper())
                time.sleep(2)
    except Exception:
        if process is not None and process.poll() is None:
            subprocess.run(['docker', 'kill', name], capture_output=True, timeout=15)
            process.wait(timeout=15)
        raise
    finally:
        receipt['seconds'] = round(time.monotonic() - started)
    receipt['exit_code'] = process.returncode
    hits = exec_attempts(work / 'build') if (work / 'build').exists() else []
    if EXEC_ATTEMPT.search((work / (log_name + '.log')).read_text(errors='replace')):
        hits.append(log_name + '.log')
    receipt['target_execution_attempts'] = hits
    require(not hits, 'TARGET_EXECUTION_ATTEMPT')
    return process.returncode


def base_receipt(args, profile, pins):
    return {'schema': 1, 'image': IMAGE, 'engine_commit': profile['commit'],
            'lock_sha256': sha(ROOT / 'build/h700-engine/mkxp-z-lock.json'),
            'profile_sha256': sha(ROOT / 'build/h700-engine/mkxp-z-profile.json'),
            'sdl_sha256': SDL_SHA256, 'pinned_inputs': pins, 'driver_sha256': sha(__file__),
            'reserve_gib': args.reserve_gib, 'arm_execution': 'NEVER', 'distribution': 'BLOCKED'}


def resolve_tools(args):
    require(os.getuid() != 0, 'UNPRIVILEGED_HOST_USER_REQUIRED')
    require(args.reserve_gib >= 5, 'RESERVE_BELOW_OWNER_APPROVAL')
    for key in ('native', 'toolchain', 'sysroot'):
        setattr(args, key, getattr(args, key).resolve(strict=True))


def configure(args):
    resolve_tools(args)
    for key in ('source', 'packagecache', 'sdl_run'):
        setattr(args, key, getattr(args, key).resolve(strict=True))
    work = args.workspace.absolute()
    require(work.parent.is_dir() and not work.exists(), 'FRESH_PRIVATE_WORKSPACE_REQUIRED')
    require(not work.resolve().is_relative_to(ROOT), 'OUTPUT_MUST_BE_OUTSIDE_REPOSITORY')
    require(shutil.disk_usage(work.parent).free >= (args.reserve_gib + 2) * GIB, 'INITIAL_SPACE')
    profile = json.loads((ROOT / 'build/h700-engine/mkxp-z-profile.json').read_text())
    expected = json.loads((ROOT / 'build/h700-engine/mkxp-z-lock.json').read_text())
    current = lock(args.source, profile)
    require(current == expected and current['status'] == 'LOCK_COMPLETE', 'LOCK_DRIFT')
    archives = [a for e in current['wraps'].values() if e['kind'] == 'wrap-file'
                for a in (e, e.get('patch_archive')) if a]
    for item in archives:
        require(sha(args.packagecache / item['filename']) == item['sha256'],
                'PACKAGECACHE_HASH:' + item['filename'])
    pins = input_pins(args)
    work.mkdir(mode=0o700)
    shutil.copytree(args.source, work / 'src', symlinks=True)
    cache = work / 'src/subprojects/packagecache'
    cache.mkdir()
    for item in archives:
        shutil.copyfile(args.packagecache / item['filename'], cache / item['filename'])
    for entry in current['wraps'].values():
        if entry['kind'] == 'wrap-git':
            target = work / 'src/subprojects' / entry['directory']
            shutil.copytree(args.packagecache / 'git' / entry['directory'], target, symlinks=True)
            apply_diffs(target, work / 'src/subprojects/packagefiles', entry['diff_files'])
    local = add_local_patches(work / 'src/subprojects', profile)
    stage_sdl(args.sdl_run, work / 'sdl-prefix')
    (work / 'cross.ini').write_text(cross_file())
    guard(work, args.budget_gib * GIB, args.reserve_gib)
    receipt = dict(base_receipt(args, profile, pins), status='CONFIGURE_STARTED',
                   local_patches=local)
    try:
        code = run_container(args, work, setup_command(profile), 'configure', receipt)
        require(code == 0, 'MESON_SETUP_FAILED_SEE_PRIVATE_LOG')
        require(input_pins(args) == pins, 'BUILD_INPUTS_CHANGED')
        receipt.update(status='MESON_SETUP_PASS', compile='NOT_ATTEMPTED',
                       free_bytes=shutil.disk_usage(work).free, job_bytes=tree_size(work))
    except Exception as error:
        receipt.update(status='CONFIGURE_BLOCKED', reason=str(error))
        raise
    finally:
        (work / 'configure-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {k: receipt.get(k) for k in ('status', 'seconds', 'free_bytes', 'job_bytes')}


def engine_outputs(build):
    """Hash AArch64 ELF executables in the build root; never executes them."""
    found = {}
    for path in sorted(build.iterdir()):
        if path.is_file() and not path.is_symlink():
            with path.open('rb') as stream:
                header = stream.read(20)
            if header[:4] == b'\x7fELF' and header[16:20] in (b'\x02\x00\xb7\x00', b'\x03\x00\xb7\x00'):
                found[path.name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    return found


def compile_job(args):
    resolve_tools(args)
    work = args.job.resolve(strict=True)
    require(not work.is_relative_to(ROOT), 'OUTPUT_MUST_BE_OUTSIDE_REPOSITORY')
    configured = json.loads((work / 'configure-result.json').read_text())
    require(configured['status'] == 'MESON_SETUP_PASS', 'JOB_NOT_CONFIGURED')
    require(not (work / 'compile-result.json').exists(), 'COMPILE_ALREADY_RECORDED')
    profile = json.loads((ROOT / 'build/h700-engine/mkxp-z-profile.json').read_text())
    pins = input_pins(args)
    receipt = dict(base_receipt(args, profile, pins), status='COMPILE_STARTED',
                   configure_result_sha256=sha(work / 'configure-result.json'))
    require(receipt['lock_sha256'] == configured['lock_sha256'] and
            receipt['profile_sha256'] == configured['profile_sha256'] and
            pins == configured['pinned_inputs'], 'JOB_INPUTS_DIFFER_FROM_CONFIGURE')
    guard(work, args.budget_gib * GIB, args.reserve_gib)
    try:
        code = run_container(args, work, COMPILE_COMMAND, 'compile', receipt)
        require(code == 0, 'MESON_COMPILE_FAILED_SEE_PRIVATE_LOG')
        require(input_pins(args) == pins, 'BUILD_INPUTS_CHANGED')
        receipt.update(status='MESON_COMPILE_PASS', outputs=engine_outputs(work / 'build'),
                       abi='NOT_CHECKED', device_execution='NOT_TESTED',
                       free_bytes=shutil.disk_usage(work).free, job_bytes=tree_size(work))
        require(receipt['outputs'], 'NO_AARCH64_ENGINE_EXECUTABLE')
    except Exception as error:
        receipt.update(status='COMPILE_BLOCKED', reason=str(error))
        raise
    finally:
        (work / 'compile-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {k: receipt.get(k) for k in ('status', 'seconds', 'free_bytes', 'job_bytes', 'outputs')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('setup', 'compile'), default='setup')
    for key in ('native', 'toolchain', 'sysroot'):
        parser.add_argument('--' + key, required=True, type=Path)
    for key in ('source', 'packagecache', 'sdl-run', 'workspace', 'job'):
        parser.add_argument('--' + key, type=Path)
    parser.add_argument('--reserve-gib', type=int, default=25)
    parser.add_argument('--budget-gib', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    needed = ('job',) if args.phase == 'compile' else ('source', 'packagecache', 'sdl_run', 'workspace')
    try:
        require(all(getattr(args, k) is not None for k in needed), 'MISSING_ARGUMENT_FOR_PHASE')
        result = compile_job(args) if args.phase == 'compile' else configure(args)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        result = {'status': args.phase.upper() + '_BLOCKED', 'reason': str(error)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] in ('MESON_SETUP_PASS', 'MESON_COMPILE_PASS') else 2


if __name__ == '__main__':
    raise SystemExit(main())
