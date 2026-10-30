#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline inspection/extraction of owner-supplied private ZIP/RAR/CAB inputs.

Never downloads, decrypts RGSS archives, executes bundled programs or replaces
an existing output. Run in the pinned unprivileged tools container for RAR.
All extracted bytes stay private, outside this repository.
"""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
MAX_FILES, MAX_TOTAL, MAX_FILE = 100000, 8 * GIB, 2 * GIB


class Blocked(ValueError):
    pass


def require(value, code):
    if not value:
        raise Blocked(code)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_name(name):
    require(isinstance(name, str) and name and len(name) <= 4096, 'ARCHIVE_PATH')
    require(not any(ord(c) < 32 or ord(c) == 127 for c in name), 'ARCHIVE_PATH')
    require(not any(c in name for c in '\\:*?"<>|'), 'ARCHIVE_PATH')
    pure = PurePosixPath(name)
    require(not pure.is_absolute() and '..' not in pure.parts and
            pure.as_posix() == name.rstrip('/'), 'ARCHIVE_PATH')
    for part in pure.parts:
        require(not part.endswith((' ', '.')), 'FAT_PATH')
        require(part.split('.')[0].upper() not in
                {'CON', 'PRN', 'AUX', 'NUL', *('COM' + str(n) for n in range(1, 10)),
                 *('LPT' + str(n) for n in range(1, 10))}, 'FAT_PATH')
    name.encode('utf-8', 'strict')
    return pure.as_posix()


def zip_entries(path):
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            require(not info.flag_bits & 1, 'ENCRYPTED_CONTAINER')
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            require(kind in (0, stat.S_IFDIR, stat.S_IFREG), 'ARCHIVE_SPECIAL_FILE')
            if info.is_dir():
                yield info.filename, info.file_size, True, None
            else:
                with archive.open(info) as stream:
                    yield info.filename, info.file_size, False, stream.read


def native_entries(path, formats):
    library = ctypes.util.find_library('archive')
    require(library is not None, 'LIBARCHIVE_REQUIRED')
    lib = C.CDLL(library)
    signatures = {
        'archive_read_new': (C.c_void_p, []),
        'archive_read_support_filter_none': (C.c_int, [C.c_void_p]),
        'archive_read_open_filename': (C.c_int, [C.c_void_p, C.c_char_p, C.c_size_t]),
        'archive_read_next_header': (C.c_int, [C.c_void_p, C.POINTER(C.c_void_p)]),
        'archive_entry_pathname': (C.c_char_p, [C.c_void_p]),
        'archive_entry_size': (C.c_longlong, [C.c_void_p]),
        'archive_entry_filetype': (C.c_uint, [C.c_void_p]),
        'archive_entry_symlink': (C.c_char_p, [C.c_void_p]),
        'archive_entry_hardlink': (C.c_char_p, [C.c_void_p]),
        'archive_read_data': (C.c_ssize_t, [C.c_void_p, C.c_void_p, C.c_size_t]),
        'archive_read_data_skip': (C.c_int, [C.c_void_p]),
        'archive_read_free': (C.c_int, [C.c_void_p]),
    }
    for name in formats:
        signatures['archive_read_support_format_' + name] = (C.c_int, [C.c_void_p])
    for name, (result, args) in signatures.items():
        function = getattr(lib, name)
        function.restype, function.argtypes = result, args
    archive = lib.archive_read_new()
    require(archive, 'RAR_OPEN')
    try:
        for feature in ['archive_read_support_filter_none'] + [
                'archive_read_support_format_' + name for name in formats]:
            require(getattr(lib, feature)(archive) == 0, 'RAR_FORMAT_SUPPORT')
        require(lib.archive_read_open_filename(archive, os.fsencode(path), 65536) == 0, 'RAR_OPEN')
        entry = C.c_void_p()
        buffer = C.create_string_buffer(1024 * 1024)

        def read(_size):
            count = lib.archive_read_data(archive, buffer, len(buffer))
            require(count >= 0, 'RAR_READ')
            return buffer.raw[:count]

        while True:
            code = lib.archive_read_next_header(archive, C.byref(entry))
            if code == 1:  # ARCHIVE_EOF
                break
            require(code == 0, 'RAR_HEADER')
            require(not lib.archive_entry_symlink(entry) and not lib.archive_entry_hardlink(entry),
                    'ARCHIVE_SPECIAL_FILE')
            kind = lib.archive_entry_filetype(entry)
            require(kind in (stat.S_IFREG, stat.S_IFDIR), 'ARCHIVE_SPECIAL_FILE')
            raw = lib.archive_entry_pathname(entry)
            require(raw is not None, 'ARCHIVE_PATH')
            yield raw.decode('utf-8', 'strict'), lib.archive_entry_size(entry), kind == stat.S_IFDIR, read
            require(lib.archive_read_data_skip(archive) == 0, 'RAR_SKIP')
    finally:
        lib.archive_read_free(archive)


def entries(path):
    with path.open('rb') as stream:
        header = stream.read(8)
    if header.startswith(b'PK\x03\x04'):
        return zip_entries(path)
    if header.startswith(b'Rar!\x1a\x07'):
        return native_entries(path, ('rar', 'rar5'))
    require(header.startswith(b'MSCF'), 'ZIP_RAR_OR_CAB_REQUIRED')
    return native_entries(path, ('cab',))


def inspect(path):
    listing, folded, total = [], {}, 0
    for raw, size, directory, _ in entries(path):
        name = safe_name(raw)
        require(0 <= size <= MAX_FILE, 'ENTRY_SIZE_LIMIT')
        require(directory or size >= 0, 'ENTRY_SIZE_LIMIT')
        key = name.casefold()
        require(key not in folded, 'DUPLICATE_OR_CASE_COLLISION')
        folded[key] = (name, directory)
        total += size
        require(len(listing) < MAX_FILES and total <= MAX_TOTAL, 'ARCHIVE_SIZE_LIMIT')
        listing.append((name, size, directory))
    require(listing, 'EMPTY_ARCHIVE')
    # FAT collisions can also occur in implicit parent directories.
    seen = {}
    for name, _, directory in listing:
        pure = PurePosixPath(name)
        for part in (pure, *pure.parents):
            if part == PurePosixPath('.'):
                continue
            key = part.as_posix().casefold()
            require(key not in seen or seen[key] == part.as_posix(), 'PARENT_CASE_COLLISION')
            seen[key] = part.as_posix()
            if part != pure:
                require(key not in folded or folded[key][1], 'FILE_DIRECTORY_COLLISION')
    return listing, total


def process(path, expected, output=None, reserve_gib=5):
    path = Path(path)
    require(re.fullmatch(r'[0-9a-f]{64}', expected), 'EXPECTED_HASH_REQUIRED')
    require(path.is_file() and not path.is_symlink(), 'REGULAR_INPUT_REQUIRED')
    require(digest(path) == expected, 'ARCHIVE_HASH')
    listing, total = inspect(path)
    if output is not None:
        output = Path(output).absolute()
        require(not output.exists() and not output.is_symlink(), 'FRESH_OUTPUT_REQUIRED')
        require(output.parent.is_dir() and not output.resolve().is_relative_to(ROOT), 'PRIVATE_OUTPUT_REQUIRED')
        require(not any(p.is_symlink() for p in output.parents), 'OUTPUT_SYMLINK')
        require(reserve_gib >= 5, 'RESERVE_BELOW_APPROVAL')
        require(shutil.disk_usage(output.parent).free > total + (reserve_gib + 1) * GIB, 'FREE_SPACE_GUARD')
        require(digest(path) == expected, 'ARCHIVE_CHANGED')
        output.mkdir(mode=0o700)
        count = 0
        for raw, size, directory, read in entries(path):
            require(count < len(listing), 'ARCHIVE_CHANGED')
            name = safe_name(raw)
            require((name, size, directory) == listing[count], 'ARCHIVE_CHANGED')
            count += 1
            require(shutil.disk_usage(output).free > (reserve_gib + 1) * GIB, 'FREE_SPACE_GUARD')
            dest = output / name
            if directory:
                dest.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            written = 0
            with dest.open('xb') as stream:
                while chunk := read(1024 * 1024):
                    written += len(chunk)
                    require(written <= size, 'ENTRY_SIZE_MISMATCH')
                    stream.write(chunk)
            dest.chmod(0o600)  # bundled executables are data, never executable
            require(written == size, 'ENTRY_SIZE_MISMATCH')
        require(count == len(listing) and digest(path) == expected, 'ARCHIVE_CHANGED')
    return {'schema': 1, 'status': 'EXTRACTED_PRIVATE' if output else 'INSPECTED_ONLY',
            'sha256': expected, 'entries': len(listing), 'uncompressed_bytes': total,
            'game_roots': sorted(str(PurePosixPath(n).parent) for n, _, d in listing
                                 if not d and PurePosixPath(n).name == 'Game.ini'),
            'target_execution': 'NEVER', 'h700_result': 'NOT_TESTED'}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--reserve-gib', type=int, default=5)
    args = parser.parse_args()
    try:
        result = process(args.archive, args.sha256, args.output, args.reserve_gib)
    except Blocked as error:
        print(json.dumps({'status': 'PRIVATE_ARCHIVE_BLOCKED', 'code': str(error)}))
        return 2
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile, AttributeError):
        print(json.dumps({'status': 'PRIVATE_ARCHIVE_BLOCKED'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
