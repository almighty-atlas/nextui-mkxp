#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record/verify the complete private build environment, not just an archive hash.

Offline, read-only inspection of explicitly supplied roots. No downloads,
installation, target execution or distribution clearance. A matching receipt
proves input identity; it is NOT a clean-room source rebuild certificate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from h700_ruby_batch import IMAGE, COMPILER_ARCHIVE, sha

ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TZ': 'UTC'}
COMPONENTS = ('toolchain', 'sysroot', 'native', 'sdl')
TOOLS_SCRIPT = """set -eu
dpkg-query -W -f='${binary:Package} ${Version}\\n' | LC_ALL=C sort
"""


class Blocked(ValueError):
    """Allowlisted diagnostic code, never an exception containing private data."""


def require(value, code):
    if not value:
        raise Blocked(code)


def fingerprint(root):
    """Relative names, types, content, executable bits and internal link targets.

    Unlike the historical tree_digest, this includes directories/empty folders
    and execute bits, and rejects special files without opening them.
    """
    root = Path(root)
    require(not root.is_symlink() and root.is_dir(), 'INVALID_COMPONENT_ROOT')
    root = root.resolve(strict=True)
    records, total = [], 0
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '.git' in relative.parts:
            continue
        name = relative.as_posix()
        require(not any(ord(c) < 32 or ord(c) == 127 for c in name), 'CONTROL_CHARACTER')
        st = path.lstat()
        if stat.S_ISLNK(st.st_mode):
            require(path.resolve().is_relative_to(root), 'COMPONENT_LINK_ESCAPE')
            records.append([name, 'link', str(path.readlink())])
        elif stat.S_ISDIR(st.st_mode):
            records.append([name, 'directory'])
        else:
            require(stat.S_ISREG(st.st_mode), 'COMPONENT_SPECIAL_FILE')
            records.append([name, 'file', st.st_mode & 0o111, sha(path)])
            total += st.st_size
    require(records, 'EMPTY_COMPONENT')
    payload = json.dumps(records, ensure_ascii=True, separators=(',', ':')).encode()
    return {'algorithm': 'relative-tree-v1', 'sha256': hashlib.sha256(payload).hexdigest(),
            'entries': len(records), 'bytes': total}


def run(command):
    return subprocess.check_output(command, env=ENV, stderr=subprocess.PIPE,
                                   timeout=120).decode('utf-8')


def image_identity():
    # Read selected fields only, never image environment or daemon credentials.
    raw = run(['docker', 'image', 'inspect', IMAGE, '--format',
               '{{json .Id}} {{json .Os}} {{json .Architecture}}'])
    require(raw.strip() == f'"{IMAGE}" "linux" "amd64"', 'IMAGE_IDENTITY')
    command = ['docker', 'run', '--rm', '--pull=never', '--network=none', '--read-only',
               '--cpus=2', '--memory=4g', '--memory-swap=4g', '--cap-drop=ALL',
               '--security-opt=no-new-privileges', '--user=' + str(os.getuid()) + ':' + str(os.getgid()),
               '--env', 'LC_ALL=C', '--env', 'PATH=/usr/bin:/bin',
               '--entrypoint=/bin/sh', IMAGE, '-c', TOOLS_SCRIPT]
    packages = run(command).splitlines()
    require(packages and packages == sorted(set(packages)), 'PACKAGE_INVENTORY')
    return {'id': IMAGE, 'os': 'linux', 'arch': 'amd64', 'packages': packages}


def capture(roots, archive):
    require(set(roots) == set(COMPONENTS), 'COMPONENT_SET')
    require(sha(archive) == COMPILER_ARCHIVE, 'COMPILER_ARCHIVE_HASH')
    before = {key: fingerprint(roots[key]) for key in COMPONENTS}
    image = image_identity()
    after = {key: fingerprint(roots[key]) for key in COMPONENTS}
    require(before == after, 'ENVIRONMENT_CHANGED_DURING_CAPTURE')
    return {'schema': 1, 'scope': 'private-build-environment-identity',
            'image': image, 'compiler_archive_sha256': COMPILER_ARCHIVE,
            'components': before, 'arm_execution': 'NEVER', 'distribution': 'BLOCKED',
            'clean_room_rebuild': 'NOT_VERIFIED'}


def compare(expected, actual):
    # Compare the WHOLE receipt: do not accept a package-only or archive-only
    # match when the actual extracted compiler, headers, Ruby or SDL changed.
    require(expected == actual, 'ENVIRONMENT_DRIFT')
    return {'status': 'ENVIRONMENT_MATCH', 'clean_room_rebuild': 'NOT_VERIFIED',
            'distribution': 'BLOCKED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('capture', 'verify'))
    for key in COMPONENTS:
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--compiler-archive', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True,
                        help='Fresh output for capture; trusted reference for verify')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.action == 'capture':
            require(not args.receipt.exists() and not args.receipt.is_symlink(), 'RECEIPT_EXISTS')
        else:
            require(args.receipt.is_file() and not args.receipt.is_symlink(), 'INVALID_RECEIPT')
        actual = capture({key: getattr(args, key) for key in COMPONENTS}, args.compiler_archive)
        if args.action == 'capture':
            with args.receipt.open('x') as stream:
                json.dump(actual, stream, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            result = {'status': 'ENVIRONMENT_RECORDED', 'receipt_sha256': sha(args.receipt),
                      'clean_room_rebuild': 'NOT_VERIFIED', 'distribution': 'BLOCKED'}
        else:
            result = compare(json.loads(args.receipt.read_text()), actual)
    except Blocked as error:
        print(json.dumps({'status': 'ENVIRONMENT_BLOCKED', 'code': str(error)}))
        return 2
    except (ValueError, OSError, subprocess.SubprocessError):
        # Paths, container stderr and actual package content stay private.
        print(json.dumps({'status': 'ENVIRONMENT_BLOCKED'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
