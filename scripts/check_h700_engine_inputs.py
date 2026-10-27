#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only offline input preflight. Never downloads, extracts or executes inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tarfile


MAX_FILE = 1024 * 1024 * 1024
MAX_MEMBERS = 100000
REQUIRED = {'gcc', 'linux', 'glibc', 'mkxp-z', 'sdl'}
REQUIRED_ROLES = {'gcc': 'cross-toolchain', 'linux': 'source', 'glibc': 'source',
                  'mkxp-z': 'engine-source', 'sdl': 'source'}
GATES = {'issue_1', 'issue_2', 'issue_3', 'dependency_closure', 'builder_identity'}
PLATFORMS = {
    'cross-toolchain': 'host-target', 'host-tool': 'host',
    'source': 'neutral', 'engine-source': 'neutral', 'patch': 'neutral',
    'sysroot': 'target', 'target-runtime': 'target',
}


class Rejected(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Rejected(code)


def keys(value, names):
    require(isinstance(value, dict) and set(value) == set(names.split()), 'SCHEMA')


def text(value):
    return isinstance(value, str) and 0 < len(value) <= 1000 and all(
        ord(c) >= 32 for c in value)


def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def relative(value):
    require(text(value) and '\\' not in value and ':' not in value, 'UNSAFE_PATH')
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(p not in ('', '.', '..')
            for p in value.split('/')), 'UNSAFE_PATH')
    return path


def approval(value):
    keys(value, 'state reviewer evidence')
    require(value['state'] == 'APPROVED' and text(value['reviewer'])
            and text(value['evidence']), 'APPROVAL_REQUIRED')


def open_cached(root, name):
    """Linux/POSIX descriptor walk: no symlink at any cache component, no FIFO."""
    parts = relative(name).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        child = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                        dir_fd=fd)
        try:
            info = os.fstat(child)
            require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE,
                    'NOT_REGULAR_OR_TOO_LARGE')
            return os.fdopen(child, 'rb')
        except Exception:
            os.close(child)
            raise
    finally:
        os.close(fd)


def elf_platform(header, role):
    if not header.startswith(b'\x7fELF'):
        return
    require(len(header) >= 20 and header[4:6] == b'\x02\x01', 'ELF_ABI')
    machine = struct.unpack('<H', header[18:20])[0]
    allowed = {'host-tool': {62}, 'target-runtime': {183},
               'sysroot': {183}, 'cross-toolchain': {62, 183}}
    require(machine in allowed.get(role, set()), 'HOST_TARGET_MIX')


def inspect_file(stream, item):
    before = os.fstat(stream.fileno())
    hasher = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        hasher.update(chunk)
    require(hasher.hexdigest() == item['sha256'], 'HASH_MISMATCH')
    stream.seek(0)
    if item['format'] == 'blob':
        elf_platform(stream.read(20), item['role'])
    else:
        # Conservative: reject all links/devices, even internal links. No extraction.
        with tarfile.open(fileobj=stream, mode='r|*') as archive:
            total = 0
            seen = set()
            for count, member in enumerate(archive, 1):
                require(count <= MAX_MEMBERS, 'ARCHIVE_LIMIT')
                name = member.name.rstrip('/') if member.isdir() else member.name
                relative(name)
                require(name not in seen, 'ARCHIVE_DUPLICATE')
                seen.add(name)
                require(member.isfile() or member.isdir(), 'ARCHIVE_LINK_OR_SPECIAL')
                require(not member.mode & 0o6000, 'ARCHIVE_PRIVILEGED_MODE')
                total += member.size
                require(total <= MAX_FILE and member.size >= 0, 'ARCHIVE_LIMIT')
                if member.isfile():
                    with archive.extractfile(member) as content:
                        elf_platform(content.read(20), item['role'])
            require(bool(seen), 'ARCHIVE_EMPTY')
    after = os.fstat(stream.fileno())
    require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'INPUT_CHANGED')


def input_metadata(item):
    keys(item, 'id role platform source cache_path format sha256 license approval blockers')
    require(isinstance(item['id'], str) and
            re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', item['id']), 'INPUT_ID')
    require(item['role'] in PLATFORMS and
            item['platform'] == PLATFORMS[item['role']], 'HOST_TARGET_MIX')
    require(item['id'] not in REQUIRED_ROLES or
            item['role'] == REQUIRED_ROLES[item['id']], 'HOST_TARGET_MIX')
    relative(item['cache_path'])
    require(item['format'] in ('blob', 'tar'), 'FORMAT')
    keys(item['source'], 'kind revision url evidence')
    source = item['source']
    require(text(source['url']) and source['url'].startswith('https://') and
            text(source['evidence']), 'SOURCE_EVIDENCE')
    if source['kind'] == 'git':
        require(isinstance(source['revision'], str) and
                re.fullmatch('[0-9a-f]{40}', source['revision']), 'UNPINNED_SOURCE')
    else:
        require(source['kind'] == 'release' and text(source['revision']) and
                re.fullmatch(r'v?\d[0-9A-Za-z._-]*', source['revision']), 'UNPINNED_SOURCE')
    keys(item['license'], 'expression evidence obligations')
    for value in item['license'].values():
        require(text(value) and value not in ('UNKNOWN', 'TBD', 'NOASSERTION'), 'LICENSE_REQUIRED')
    require(isinstance(item['blockers'], list) and not item['blockers'], 'INPUT_BLOCKED')
    require(digest(item['sha256']), 'HASH_REQUIRED')
    approval(item['approval'])


def check(manifest, cache):
    """Deterministic codes only: never echo private paths, payload or exception text."""
    errors = []
    checked = 0
    try:
        keys(manifest, 'schema scope distribution host target gates inputs notes')
        require(type(manifest['schema']) is int and manifest['schema'] == 1, 'SCHEMA')
        require(manifest['scope'] == 'static-preparation' and
                manifest['distribution'] == 'BLOCKED', 'SCOPE_OR_RELEASE_STOP')
        require(manifest['host'] == {'os': 'linux', 'arch': 'x86_64'}, 'HOST_TARGET_MIX')
        require(manifest['target'] == {
            'os': 'linux', 'arch': 'aarch64', 'endian': 'little',
            'triple': 'aarch64-nextui-linux-gnu',
            'compiler_version': '8.3.0', 'kernel_headers': '4.9.170',
            'glibc': '2.28', 'minimum_kernel': '4.9.0',
            'interpreter': '/lib/ld-linux-aarch64.so.1'}, 'TARGET_BASELINE')
        require(isinstance(manifest['notes'], list) and
                all(text(n) for n in manifest['notes']), 'SCHEMA')
        require(isinstance(manifest['gates'], dict) and
                set(manifest['gates']) == GATES, 'GATES_REQUIRED')
        require(isinstance(manifest['inputs'], list) and
                0 < len(manifest['inputs']) <= 1000, 'INPUTS_REQUIRED')
        ids = [i.get('id') for i in manifest['inputs'] if isinstance(i, dict)]
        require(all(isinstance(i, str) for i in ids) and
                len(set(ids)) == len(ids) and REQUIRED <= set(ids), 'INPUTS_REQUIRED')
    except (Rejected, TypeError, KeyError) as exc:
        return report([{'code': str(exc) if isinstance(exc, Rejected) else 'SCHEMA'}], 0)
    for name in sorted(GATES):
        try:
            approval(manifest['gates'][name])
        except Rejected:
            errors.append({'gate': name, 'code': 'APPROVAL_REQUIRED'})
    # Anchor only an existing explicit cache root. Ancestors are caller-trusted;
    # the root itself and every input component must not be symlinks.
    cache = Path(cache).absolute()
    for index, item in enumerate(manifest['inputs']):
        try:
            input_metadata(item)
            with open_cached(cache, item['cache_path']) as stream:
                inspect_file(stream, item)
            checked += 1
        except Rejected as exc:
            errors.append({'input': index, 'code': str(exc)})
        except (OSError, tarfile.TarError, EOFError, ValueError, TypeError, KeyError):
            errors.append({'input': index, 'code': 'UNREADABLE_OR_INVALID_INPUT'})
    return report(errors, checked)


def report(errors, checked):
    return {'status': 'BLOCKED' if errors else 'PASS', 'scope': 'offline-input-check-only',
            'checked_inputs': checked, 'blockers': errors,
            'build_authorized': False, 'distribution': 'BLOCKED'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('build/h700-engine/inputs.json'))
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.manifest.open('rb') as stream:
            data = stream.read(1024 * 1024 + 1)
        require(len(data) <= 1024 * 1024, 'MANIFEST_TOO_LARGE')
        manifest = json.loads(data, object_pairs_hook=unique_object)
        result = check(manifest, args.cache)
    except (OSError, ValueError, RecursionError):
        result = report([{'code': 'INVALID_MANIFEST'}], 0)
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
