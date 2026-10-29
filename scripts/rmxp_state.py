#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline, non-destructive maintenance of the private RMXP state layout (PR #40).

Run on a preparation computer, with the game stopped. Backups contain private
game content and saves: never commit, publish or attach them to an issue.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

ID = re.compile(r'[0-9a-f]{64}')
ROOT = Path(__file__).resolve().parents[1]
SCAN_LIMIT = 1024 * 1024
MANIFEST_LIMIT = 16 * 1024 * 1024


def require(ok, code):
    if not ok:
        raise ValueError(code)


def plain_path(path):
    """Reject links, including existing ancestors, before any writes."""
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'SYMLINK_PATH')
    return path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root, exclude_lock=False):
    files, directories = {}, []
    def walk_error(error):
        raise error
    for current, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        if exclude_lock and Path(current) == root:
            dirs[:] = [d for d in dirs if d != 'lock']
        for name in sorted(dirs + names):
            path = Path(current) / name
            mode = path.lstat().st_mode
            relative = path.relative_to(root).as_posix()
            require(not any(ord(c) < 32 or ord(c) == 127 for c in relative), 'CONTROL_CHARACTER')
            require('\\' not in relative, 'UNSUPPORTED_FILENAME')
            if stat.S_ISDIR(mode):
                directories.append(relative)
            else:
                require(stat.S_ISREG(mode), 'SPECIAL_FILE_OR_SYMLINK')
                files[relative] = {'size': path.stat().st_size, 'sha256': digest(path)}
    return {'directories': sorted(directories), 'files': dict(sorted(files.items()))}


def validate_state(state):
    state = plain_path(state)
    require(state.is_dir() and ID.fullmatch(state.name), 'INVALID_STATE_DIRECTORY')
    require([p.name for p in list(state.parents)[:3]] == ['nextui-mkxp', 'h700', '.userdata'],
            'INVALID_STATE_LAYOUT')
    require((state / 'game').is_dir() and not (state / 'game').is_symlink(), 'GAME_COPY_MISSING')
    require((state / 'game/Game.ini').is_file() and not (state / 'game/Game.ini').is_symlink(), 'GAME_INI_MISSING')
    for filename in ('source.path', 'mkxp.json'):
        require((state / filename).is_file() and not (state / filename).is_symlink(), 'STATE_METADATA_MISSING')
    return state


@contextmanager
def state_lock(state):
    # Same atomic directory lock as the Pak launcher. Never break stale locks.
    lock = state / 'lock'
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        raise ValueError('STATE_LOCKED') from None
    try:
        yield
    finally:
        lock.rmdir()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def copy_inventory(source, destination, listing):
    destination.mkdir(mode=0o700)
    for relative in listing['directories']:
        (destination / relative).mkdir(mode=0o700, parents=True, exist_ok=True)
    for relative, expected in listing['files'].items():
        src, dest = source / relative, destination / relative
        require(not src.is_symlink() and src.is_file(), 'SOURCE_CHANGED')
        with src.open('rb') as reader, dest.open('xb') as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        # Do not preserve read-only input permissions on the writable recovery copy.
        dest.chmod(0o600)
        require(dest.stat().st_size == expected['size'] and digest(dest) == expected['sha256'],
                'COPY_MISMATCH')


def space_required(parent, listing):
    require(shutil.disk_usage(parent).free > sum(f['size'] for f in listing['files'].values()) + 32 * 1024**2,
            'INSUFFICIENT_FREE_SPACE')


def snapshot(state, output):
    state, output = validate_state(state), plain_path(output)
    require(not output.is_relative_to(state), 'BACKUP_INSIDE_STATE')
    require(not output.is_relative_to(ROOT) and '.system' not in output.parts, 'PRIVATE_OUTPUT_LOCATION')
    require(output.parent.is_dir() and not output.exists(), 'FRESH_BACKUP_REQUIRED')
    with state_lock(state):
        listing = inventory(state, exclude_lock=True)
        require(not (state / 'recovery.pending').exists(), 'INCOMPLETE_RECOVERY_PRESENT')
        manifest = dict(schema=1, game_id=state.name, **listing)
        require(len((json.dumps(manifest, indent=2, ensure_ascii=True) + '\n').encode('utf-8')) <= MANIFEST_LIMIT,
                'MANIFEST_TOO_LARGE')
        space_required(output.parent, listing)
        output.mkdir(mode=0o700)
        copy_inventory(state, output / 'payload', listing)
        require(inventory(state, exclude_lock=True) == listing, 'SOURCE_CHANGED')
        # Manifest appears only after the complete copied payload is verified.
        write_json(output / 'manifest.pending', manifest)
        (output / 'manifest.pending').rename(output / 'manifest.json')
    return {'status': 'SNAPSHOT_VERIFIED', 'files': len(listing['files'])}


def verify(backup):
    backup = plain_path(backup)
    manifest_path = backup / 'manifest.json'
    require(manifest_path.is_file() and not manifest_path.is_symlink(), 'INCOMPLETE_BACKUP')
    require(manifest_path.stat().st_size <= MANIFEST_LIMIT, 'MANIFEST_TOO_LARGE')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(isinstance(manifest, dict) and set(manifest) == {'schema', 'game_id', 'files', 'directories'},
            'INVALID_MANIFEST')
    require(manifest['schema'] == 1 and isinstance(manifest['game_id'], str)
            and ID.fullmatch(manifest['game_id']), 'INVALID_MANIFEST')
    require(isinstance(manifest['files'], dict) and isinstance(manifest['directories'], list), 'INVALID_MANIFEST')
    for relative in list(manifest['files']) + manifest['directories']:
        require(isinstance(relative, str) and relative and '\\' not in relative, 'UNSAFE_MANIFEST_PATH')
        parsed = PurePosixPath(relative)
        require(parsed.parts and not parsed.is_absolute() and '..' not in parsed.parts and parsed.as_posix() == relative
                and parsed.parts[0] not in ('lock', 'recovery.pending'), 'UNSAFE_MANIFEST_PATH')
    payload = backup / 'payload'
    require(payload.is_dir() and not payload.is_symlink(), 'INVALID_PAYLOAD')
    actual = inventory(payload)
    require(actual == {k: manifest[k] for k in ('files', 'directories')}, 'BACKUP_CONTENT_MISMATCH')
    require({'source.path', 'mkxp.json', 'game/Game.ini'} <= set(actual['files']) and 'game' in actual['directories'],
            'INVALID_STATE_PAYLOAD')
    return manifest


def restore(backup, sd_root):
    """Restore only into a fresh state ID on a mounted card; never replace saves."""
    manifest = verify(backup)
    sd_root = plain_path(sd_root)
    require(sd_root.is_dir(), 'SD_ROOT_MISSING')
    require(not sd_root.is_relative_to(ROOT) and '.system' not in sd_root.parts, 'PRIVATE_OUTPUT_LOCATION')
    target = plain_path(sd_root / '.userdata/h700/nextui-mkxp' / manifest['game_id'])
    require(not target.exists(), 'EXISTING_STATE_PRESERVED')
    require(not target.is_relative_to(plain_path(backup)), 'RESTORE_INSIDE_BACKUP')
    space_required(sd_root, manifest)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Keep an incomplete restore locked. Only a fully verified restore unlocks.
    target.mkdir(mode=0o700)
    (target / 'lock').mkdir(mode=0o700)
    staging = target / 'recovery.pending'
    copy_inventory(Path(backup) / 'payload', staging, manifest)
    require(inventory(staging) == {k: manifest[k] for k in ('files', 'directories')}, 'RESTORE_MISMATCH')
    for child in staging.iterdir():
        require(child.name not in ('lock', 'recovery.pending'), 'RESERVED_STATE_PATH')
        child.rename(target / child.name)
    staging.rmdir()
    (target / 'lock').rmdir()
    return {'status': 'RESTORE_VERIFIED', 'files': len(manifest['files'])}


def diagnostics(state):
    """Allowlisted summary only: never emit raw text, paths, IDs or file names."""
    state = validate_state(state)
    report = {'schema': 1, 'locked': (state / 'lock').exists(), 'outcome': 'no_log',
              'exit_code': None, 'scan_truncated': False, 'categories': []}
    log = state / 'run.log'
    require(not log.is_symlink(), 'LOG_SYMLINK')
    if not log.exists():
        return report
    require(stat.S_ISREG(log.stat().st_mode), 'LOG_NOT_REGULAR')
    with log.open('rb') as stream:
        data = stream.read(SCAN_LIMIT)
        size = stream.seek(0, os.SEEK_END)
        stream.seek(max(0, size - 4096))
        tail = stream.read(4096)
    report['scan_truncated'] = size > SCAN_LIMIT
    patterns = {'missing_library': b'error while loading shared libraries:',
                'script_error': b'Script error',
                'missing_font': b'Primary font not found:',
                'audio_warning': b'AL lib:',
                'memory_failure': b'Cannot allocate memory'}
    report['categories'] = sorted(name for name, pattern in patterns.items() if pattern in data)
    last = tail.splitlines()[-1] if tail.splitlines() else b''
    match = re.fullmatch(rb'RMXP_EXIT=([0-9]{1,3})', last)
    if report['locked']:
        report['outcome'] = 'locked_or_running'
    elif match and int(match[1]) <= 255:
        code = int(match[1])
        report['exit_code'] = code
        report['outcome'] = ('returned_zero' if code == 0 else
                             'signal_or_high_exit' if code >= 128 else 'failed')
    else:
        report['outcome'] = 'incomplete_or_unrecognized'
    return report


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('snapshot')
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('verify')
    p.add_argument('--backup', type=Path, required=True)
    p = commands.add_parser('restore')
    p.add_argument('--backup', type=Path, required=True)
    p.add_argument('--sd-root', type=Path, required=True)
    p = commands.add_parser('diagnostics')
    p.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'snapshot':
            result = snapshot(args.state, args.output)
        elif args.command == 'restore':
            result = restore(args.backup, args.sd_root)
        elif args.command == 'diagnostics':
            result = diagnostics(args.state)
        else:
            verify(args.backup)
            result = {'status': 'BACKUP_VERIFIED'}
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Exception text may contain private paths. Only our known error codes escape.
        code = str(error) if type(error) is ValueError and re.fullmatch(r'[A-Z_]+', str(error)) else 'INVALID_OR_UNREADABLE_INPUT'
        print(json.dumps({'status': 'ERROR', 'code': code}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
