#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private tiny02 offline extension build, preserving all existing artifacts.

Requires explicit observed input paths and existing image. No SSH, downloads,
host installations or device execution. A successful build is not an ABI PASS.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time
import uuid


IMAGE = 'sha256:1c4ddd5655ad020d5e320e2181a04e4356af7c0e70f2be3cd5e901657cd8596b'
ARCHIVE = '4ee161939826bcdfdafa757cf8e293a7f14e357f62be7144f040335cc8c7371a'
NATIVE_RUBY = '4363b3068689a2f238f9f93a00eda3be1c072bf69716d91bb746a8c5a35687c9'
COMPILER_ARCHIVE = 'd4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3'
SYSROOT_RECEIPT = '414a9f0581f8ec5a4bef27f60a6080042f2fe3de7ee607468249b932131d5183'
EXISTING = {
    'libruby.so.3.1.3': '4c67d3c1f21393dfaac1485298b770ab1fcec6e74b775ca66d3eff58ff4a9793',
    '.ext/aarch64-linux/zlib.so': 'fcc514925e8274c6d06819c0988ae2ed06aa68bdee3fdd92b311649f7e708752',
    '.ext/aarch64-linux/psych.so': '49ab079312da72116993e0cadba827fb16b87a76de0adc7622bb686035bb727f',
}
GIB = 1024**3


def require(ok, code):
    if not ok:
        raise ValueError(code)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def unchanged(build):
    for name, expected in EXISTING.items():
        require(sha(build / name) == expected, 'EXISTING_ARTIFACT_CHANGED:' + name)


def source_check(archive, source):
    require(sha(archive) == ARCHIVE, 'RUBY_ARCHIVE_HASH')
    count = 0
    with tarfile.open(archive, 'r:xz') as tar:
        for member in tar:
            relative = Path(member.name).relative_to('ruby-3.1.3')
            require('..' not in relative.parts, 'UNSAFE_SOURCE_MEMBER')
            path = source / relative
            require(path.resolve().is_relative_to(source.resolve()), 'SOURCE_LINK_ESCAPE')
            if member.isfile():
                require(path.is_file() and not path.is_symlink() and
                        hashlib.sha256(tar.extractfile(member).read()).hexdigest() == sha(path),
                        'SOURCE_MISMATCH:' + str(relative))
                count += 1
            elif member.issym():
                require(path.is_symlink() and str(path.readlink()) == member.linkname,
                        'SOURCE_LINK_MISMATCH:' + str(relative))
    return count


def input_pins(args):
    from h700_cxx_abi import tree_digest
    require(sha(args.native / 'prefix/bin/ruby') == NATIVE_RUBY, 'NATIVE_RUBY_HASH')
    archive = args.toolchain.parents[1] / 'inputs/gcc-8.3.0-aarch64-nextui-linux-gnu-x86_64-host.tar.xz'
    require(sha(archive) == COMPILER_ARCHIVE, 'COMPILER_ARCHIVE_HASH')
    path = args.sysroot.parent / 'sysroot-provenance.json'
    require(sha(path) == SYSROOT_RECEIPT, 'SYSROOT_RECEIPT_HASH')
    receipt = json.loads(path.read_text())
    require(tree_digest(args.sysroot) == receipt['sysroot_tree_sha256'], 'SYSROOT_TREE_CHANGED')
    return {'native_ruby_sha256': NATIVE_RUBY, 'compiler_archive_sha256': COMPILER_ARCHIVE,
            'sysroot_receipt_sha256': SYSROOT_RECEIPT,
            'sysroot_tree_sha256': receipt['sysroot_tree_sha256']}


def configure_guard(log):
    require('ac_cv_env_build_alias_value=x86_64-pc-linux-gnu' in log,
            'EXPLICIT_LIBFFI_BUILD_ALIAS_MISSING')
    require(not re.search(r'^configure:\d+: \./conftest(?:\s|$)', log, re.M) and
            'cannot execute binary file' not in log, 'TARGET_EXECUTION_ATTEMPT_IN_CONFIGURE')


def size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())


def guard(work):
    # Stop one GiB above the hard floor, allowing for sampling/other host writers.
    require(shutil.disk_usage(work).free >= 26 * GIB, 'FREE_SPACE_GUARD_26_GIB')
    require(size(work) <= GIB, 'PRIVATE_JOB_BUDGET_1_GIB')


def command(args, work, name):
    script = Path(__file__).with_name('h700_ruby_extensions.sh').resolve(strict=True)
    mounts = [(args.native, '/work', True), (work / 'target', '/target', False),
              (args.toolchain, '/build/toolchains/gcc-8.3', True),
              (args.sysroot, '/build/sysroot-runs/sysroot-20261027-212308/sysroot', True),
              (args.zlib, '/zlib', True), (script, '/batch.sh', True)]
    cmd = ['docker', 'run', '--name', name, '--rm', '--pull=never', '--network=none',
           '--read-only', '--cpus=2', '--memory=4g', '--memory-swap=4g',
           '--cap-drop=ALL', '--security-opt=no-new-privileges',
           '--user=' + str(os.getuid()) + ':' + str(os.getgid()),
           '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m', '--workdir=/target',
           '--entrypoint=/bin/sh']
    for source, target, readonly in mounts:
        require(',' not in str(source), 'UNSUPPORTED_MOUNT_PATH')
        cmd += ['--mount', 'type=bind,src=' + str(source) + ',dst=' + target +
                (',readonly' if readonly else '')]
    phase = ('support-only' if args.support_only else
             'reuse-encodings' if args.reuse_encodings else 'full')
    return cmd + [IMAGE, '/batch.sh', phase]


def build(args):
    require(os.getuid() != 0, 'UNPRIVILEGED_HOST_USER_REQUIRED')
    for key in ('native', 'seed', 'toolchain', 'sysroot', 'zlib'):
        setattr(args, key, getattr(args, key).resolve(strict=True))
    work = args.workspace.absolute()
    require(not (args.reuse_encodings and args.support_only), 'CHOOSE_ONE_REUSE_PHASE')
    require(work.parent.is_dir() and not work.exists() and not work.is_symlink(),
            'FRESH_PRIVATE_WORKSPACE_REQUIRED')
    require(not work.resolve().is_relative_to(Path(__file__).resolve().parents[1]),
            'OUTPUT_MUST_BE_OUTSIDE_REPOSITORY')
    require(shutil.disk_usage(work.parent).free >= 27 * GIB, 'INITIAL_SPACE_27_GIB')
    require(size(args.seed) < 128 * 1024**2, 'SEED_TOO_LARGE')
    unchanged(args.seed)
    pins = input_pins(args)
    count = source_check(args.native.parent / 'inputs/ruby-3.1.3.tar.xz',
                         args.native / 'src/ruby-3.1.3')
    work.mkdir(mode=0o700)
    previous_encodings = {}
    if args.reuse_encodings or args.support_only:
        enc = args.seed / '.ext/aarch64-linux/enc'
        require(enc.is_dir(), 'NO_ENCODINGS_TO_REUSE')
        previous_encodings = {str(p.relative_to(enc)): sha(p) for p in enc.rglob('*.so')}

    def ignore(directory, names):
        # Copy all successful outputs, but do not copy the prior Fiddle retry.
        if args.reuse_encodings and Path(directory) == args.seed / 'ext':
            return ['fiddle']
        if args.reuse_encodings and Path(directory) == args.seed / '.ext/aarch64-linux':
            return ['fiddle.so']
        return []

    shutil.copytree(args.seed, work / 'target', symlinks=True, ignore=ignore)
    guard(work)
    name = 'nextui-ruby-batch-' + uuid.uuid4().hex[:12]
    cmd = command(args, work, name)
    receipt = {'schema': 1, 'status': 'BUILD_STARTED', 'image': IMAGE,
               'pinned_inputs': pins,
               'source_archive_sha256': ARCHIVE, 'source_files_verified': count,
               'script_sha256': sha(Path(__file__).with_name('h700_ruby_extensions.sh')),
               'driver_sha256': sha(__file__), 'docker_command': cmd,
               'arm_execution': 'NEVER', 'distribution': 'BLOCKED'}
    (work / 'build-inputs.json').write_text(json.dumps(receipt, indent=2) + '\n')
    started = time.monotonic()
    process = None
    try:
        with (work / 'build.log').open('wb') as log:
            process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                       env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
            while process.poll() is None:
                guard(work)
                require(time.monotonic() - started < 600, 'BUILD_TIMEOUT_600S')
                require((work / 'build.log').stat().st_size < 64 * 1024**2, 'LOG_BUDGET')
                time.sleep(1)
            require(process.returncode == 0, 'BATCH_BUILD_FAILED_SEE_PRIVATE_LOG')
        guard(work)
        unchanged(args.seed)
        unchanged(work / 'target')
        require(input_pins(args) == pins, 'BUILD_INPUTS_CHANGED')
        configure_guard((work / 'target/ext/fiddle/libffi-3.2.1/config.log').read_text())
        outputs = work / 'target/.ext/aarch64-linux'
        if args.reuse_encodings or args.support_only:
            enc = outputs / 'enc'
            require(previous_encodings == {str(p.relative_to(enc)): sha(p)
                                            for p in enc.rglob('*.so')},
                    'REUSED_ENCODINGS_CHANGED')
        require((outputs / 'enc/utf_16le.so').is_file() and
                (outputs / 'enc/utf_16be.so').is_file() and (outputs / 'fiddle.so').is_file() and
                (outputs / 'stringio.so').is_file() and (outputs / 'date_core.so').is_file(),
                'REQUIRED_MODULES_MISSING')
        receipt['outputs'] = {str(p.relative_to(outputs)): sha(p)
                              for p in sorted(outputs.rglob('*.so'))}
        receipt.update(status='RUBY_EXTENSION_BATCH_BUILD_PASS', abi='NOT_CHECKED',
                       free_bytes=shutil.disk_usage(work).free)
    except Exception as error:
        # Only this freshly created, uniquely named test container is stopped.
        if process is not None and process.poll() is None:
            subprocess.run(['docker', 'kill', name], capture_output=True, timeout=15)
            process.wait(timeout=15)
        receipt.update(status='BUILD_BLOCKED', reason=str(error))
        raise
    finally:
        (work / 'build-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {key: receipt[key] for key in ('status', 'outputs', 'free_bytes', 'abi')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('native', 'seed', 'toolchain', 'sysroot', 'zlib', 'workspace'):
        parser.add_argument('--' + key, required=True, type=Path)
    parser.add_argument('--reuse-encodings', action='store_true')
    parser.add_argument('--support-only', action='store_true')
    args = parser.parse_args()
    try:
        result = build(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result = {'status': 'BUILD_BLOCKED', 'reason': str(error)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'RUBY_EXTENSION_BATCH_BUILD_PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
