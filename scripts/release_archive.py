#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and offline-verify a deterministic RMXP.pak release archive.

STRUCTURE checks archive layout, checksums, notices and target ELF ABI.
RELEASE_GATE stays BLOCKED until every human gate in the manifest is GO;
the H700 gate must be bound to the exact engine hash. Host tests cannot
produce that evidence.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import zipfile

PAK = 'Emus/h700/RMXP.pak'
MANIFEST = PAK + '/release/manifest.json'
REQUIRED = {PAK + '/launch.sh': 'script', PAK + '/engine': 'binary', PAK + '/SHA256SUMS': 'data',
            PAK + '/release/THIRD_PARTY_NOTICES.md': 'notice', PAK + '/release/BUILDING.md': 'doc'}
ROLES = {'binary', 'script', 'data', 'config', 'license', 'notice', 'doc'}
GATES = ('license_review', 'corresponding_source', 'relink', 'binary_provenance',
         'release_approval', 'h700_acceptance')
H700_CHECKS = ('R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7')
FORBIDDEN_SUFFIXES = {'.rxdata', '.rvdata', '.rvdata2', '.rgssad', '.rgss2a', '.rgss3a', '.sav',
                      '.srm', '.gba', '.gbc', '.gb', '.nds', '.iso', '.exe', '.dll', '.zip', '.7z',
                      '.ogg', '.mid', '.midi', '.wav', '.mp3', '.pem', '.key'}
FORBIDDEN_NAMES = {'game.ini', 'game.exe', '.env', 'id_rsa', 'id_ed25519'}
MAX_FILES, MAX_BYTES = 20000, 512 * 1024 * 1024
EPOCH = (1980, 1, 1, 0, 0, 0)
SHA = re.compile(r'[0-9a-f]{64}')
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def glibc_key(name):
    return tuple(int(x) for x in name[6:].split('.'))


def elf_findings(data, target):
    """Parse an ELF64 AArch64 executable; return rule identifiers."""
    if data[:4] != b'\x7fELF':
        return ['BINARY_NOT_ELF']
    try:
        if data[4] != 2 or data[5] != 1:
            return ['ELF_NOT_64BIT_LITTLE_ENDIAN']
        found = []
        machine, = struct.unpack_from('<H', data, 18)
        if machine != 183:
            found.append('ELF_NOT_AARCH64')
        phoff, shoff = struct.unpack_from('<QQ', data, 32)
        phnum, shentsize, shnum = struct.unpack_from('<HHH', data, 56)
        interp, executable_stack = None, True
        for i in range(phnum):
            p_type, p_flags, offset, _, _, size = struct.unpack_from('<IIQQQQ', data, phoff + 56 * i)
            if p_type == 3:
                interp = data[offset:offset + size].rstrip(b'\0').decode('ascii', 'replace')
            elif p_type == 0x6474e551:
                executable_stack = bool(p_flags & 1)
        if interp != target['interpreter']:
            found.append('ELF_INTERPRETER')
        if executable_stack:
            found.append('ELF_EXECUTABLE_STACK')
        if not shnum or shentsize != 64:
            return found + ['ELF_SECTIONS_MISSING']
        sections = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + 64 * i) for i in range(shnum)]

        def string(link, offset):
            base = sections[link][4] + offset
            return data[base:data.index(b'\0', base)].decode('ascii', 'replace')

        versions, needed = [], []
        for _, kind, _, _, offset, size, link, _, _, _ in sections:
            if kind == 6:
                for pos in range(offset, offset + size, 16):
                    tag, value = struct.unpack_from('<qQ', data, pos)
                    if tag == 0:
                        break
                    if tag == 1:
                        needed.append(string(link, value))
                    elif tag in (15, 29):
                        if any(not p.startswith('$ORIGIN') for p in string(link, value).split(':')):
                            found.append('ELF_ABSOLUTE_RPATH')
            elif kind == 0x6ffffffe:
                pos = offset
                while True:
                    _, count, _, aux, following = struct.unpack_from('<HHIII', data, pos)
                    item = pos + aux
                    for _ in range(count):
                        _, _, _, name, step = struct.unpack_from('<IHHII', data, item)
                        versions.append(string(link, name))
                        item += step
                    if not following:
                        break
                    pos += following
        limit = glibc_key('GLIBC_' + target['glibc_max'])
        for version in versions:
            if version == 'GLIBC_PRIVATE':
                found.append('ELF_GLIBC_PRIVATE')
            elif re.fullmatch(r'GLIBC_\d+(\.\d+)*', version) and glibc_key(version) > limit:
                found.append('ELF_GLIBC_TOO_NEW')
        if set(needed) - set(target['allowed_needed']):
            found.append('ELF_UNDECLARED_NEEDED')
        return found
    except (struct.error, IndexError, ValueError):
        return ['ELF_MALFORMED']


def member_findings(name, info):
    pure = PurePosixPath(name)
    if (name.startswith('/') or '\\' in name or ':' in name or '..' in pure.parts
            or not (name.startswith(PAK + '/') or name in ('Emus/', 'Emus/h700/', PAK + '/'))):
        yield 'OUTSIDE_PAK_ROOT'
    if pure.name.lower() in FORBIDDEN_NAMES or pure.suffix.lower() in FORBIDDEN_SUFFIXES:
        yield 'FORBIDDEN_CONTENT'
    if info is not None:
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode) or (mode and not stat.S_ISREG(mode) and not stat.S_ISDIR(mode)):
            yield 'SPECIAL_FILE'
        if info.flag_bits & 1:
            yield 'ENCRYPTED_MEMBER'


def gate_state(manifest, engine_hash):
    gates = manifest.get('gates') if isinstance(manifest.get('gates'), dict) else {}
    blocked = []
    for name in GATES:
        gate = gates.get(name)
        ok = (isinstance(gate, dict) and gate.get('state') == 'GO'
              and isinstance(gate.get('reviewer'), str) and gate['reviewer'].strip()
              and isinstance(gate.get('date'), str) and DATE.fullmatch(gate['date'])
              and isinstance(gate.get('evidence'), str) and gate['evidence'].strip())
        if ok and name == 'h700_acceptance':
            results = gate.get('results')
            ok = (gate.get('level') == 'verified-on-H700' and gate.get('device') == 'RG35XX Pro'
                  and isinstance(gate.get('firmware'), str) and gate['firmware'].strip()
                  and engine_hash is not None and gate.get('engine_sha256') == engine_hash
                  and isinstance(results, dict) and all(results.get(c) == 'PASS' for c in H700_CHECKS))
        if not ok:
            blocked.append(name)
    return blocked


def verify(source):
    """Return (file count, structural findings, blocked gates)."""
    findings = []
    try:
        archive = zipfile.ZipFile(source)
    except (zipfile.BadZipFile, OSError):
        return 0, [('NOT_A_ZIP', '')], list(GATES)
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_BYTES:
            return len(infos), [('ARCHIVE_TOO_LARGE', '')], list(GATES)
        files, folded = {}, set()
        for info in infos:
            name = info.filename
            findings += [(rule, name) for rule in member_findings(name, info)]
            key = name.rstrip('/').casefold()
            if key in folded:
                findings.append(('DUPLICATE_OR_CASE_COLLISION', name))
            folded.add(key)
            if not info.is_dir():
                try:
                    files[name] = archive.read(info)
                except (zipfile.BadZipFile, RuntimeError, ValueError):
                    findings.append(('CORRUPT_MEMBER', name))
    engine_hash = None
    try:
        manifest = json.loads(files.pop(MANIFEST))
        assert isinstance(manifest, dict) and manifest.get('schema') == 1
        target = manifest['target']
        assert target['arch'] == 'aarch64' and isinstance(target['interpreter'], str)
        assert re.fullmatch(r'\d+\.\d+', target['glibc_max'])
        assert all(isinstance(n, str) for n in target['allowed_needed'])
        entries = {e['path']: e for e in manifest['files']}
        assert len(entries) == len(manifest['files'])
    except (KeyError, TypeError, ValueError, AssertionError):
        return len(files), sorted(findings + [('MANIFEST_INVALID', MANIFEST)]), list(GATES)
    for path, role in REQUIRED.items():
        if path not in files or entries.get(path, {}).get('role') != role:
            findings.append(('REQUIRED_FILE_MISSING', path))
    if not any(p.startswith(PAK + '/release/LICENSES/') for p in files):
        findings.append(('LICENSES_MISSING', PAK + '/release/LICENSES/'))
    for path in sorted(set(files) - set(entries)):
        findings.append(('UNLISTED_FILE', path))
    for path, entry in sorted(entries.items()):
        data = files.get(path)
        if data is None:
            findings.append(('LISTED_FILE_MISSING', path))
            continue
        role = entry.get('role')
        if role not in ROLES or not isinstance(entry.get('sha256'), str) or not SHA.fullmatch(entry['sha256']):
            findings.append(('ENTRY_INVALID', path))
            continue
        if sha256(data) != entry['sha256']:
            findings.append(('CHECKSUM_MISMATCH', path))
        if role in ('binary', 'script', 'data', 'config') and not entry.get('license'):
            findings.append(('LICENSE_UNDECLARED', path))
        if role == 'binary':
            if entry.get('license_file') not in files or not entry.get('source'):
                findings.append(('BINARY_SOURCE_OR_LICENSE_TEXT_MISSING', path))
            findings += [(rule, path) for rule in elf_findings(data, target)]
            if path == PAK + '/engine':
                engine_hash = sha256(data)
        elif data[:4] == b'\x7fELF':
            findings.append(('UNDECLARED_BINARY', path))
        if role == 'script' and subprocess.run(['sh', '-n'], input=data, capture_output=True).returncode:
            findings.append(('SHELL_SYNTAX', path))
    sums = files.get(PAK + '/SHA256SUMS', b'').decode('utf-8', 'replace').splitlines()
    covered = {}
    for line in sums:
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if match:
            covered[PAK + '/' + match[2]] = match[1]
    expected = {p: sha256(d) for p, d in files.items() if p != PAK + '/SHA256SUMS'}
    if len(covered) != len(sums) or covered != expected:
        findings.append(('PAK_SHA256SUMS_MISMATCH', PAK + '/SHA256SUMS'))
    return len(files) + 1, sorted(set(findings)), gate_state(manifest, engine_hash)


def stage_files(stage):
    result = {}
    for path in sorted(stage.rglob('*')):
        relative = path.relative_to(stage).as_posix()
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('STAGE_SPECIAL_FILE')
        if path.is_file():
            result[relative] = path
    return result


def build(stage, output):
    files = stage_files(stage)
    try:
        manifest = json.loads(files[MANIFEST].read_bytes())
        roles = {e['path']: e['role'] for e in manifest['files']}
    except (KeyError, TypeError, ValueError):
        raise ValueError('MANIFEST_INVALID')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, path in files.items():
            info = zipfile.ZipInfo(name, EPOCH)
            info.create_system = 3
            executable = roles.get(name) in ('binary', 'script')
            info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    payload = buffer.getvalue()
    count, findings, blocked = verify(io.BytesIO(payload))
    if findings:
        return count, findings, blocked, None
    with output.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    digest = sha256(payload)
    with Path(str(output) + '.sha256').open('x') as stream:
        stream.write(f'{digest}  {output.name}\n')
    return count, findings, blocked, digest


def report(count, findings, blocked, as_json, digest=None):
    structure = 'FAIL' if findings else 'PASS'
    gate = 'BLOCKED' if blocked else 'GO'
    if as_json:
        print(json.dumps({'schema': 1, 'files': count, 'structure': structure, 'release_gate': gate,
                          'findings': [{'rule': r, 'path': p} for r, p in findings],
                          'blocked_gates': blocked, 'archive_sha256': digest}))
    else:
        for rule, path in findings:
            print(f'FAIL {rule} {path!r}')
        for name in blocked:
            print(f'GATE_BLOCKED {name}')
        if digest:
            print(f'ARCHIVE_SHA256={digest}')
        print(f'STRUCTURE={structure} RELEASE_GATE={gate} FILES={count}')
    return 1 if findings else 3 if blocked else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true')
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('verify', help='verify an archive offline')
    check.add_argument('archive', type=Path)
    make = commands.add_parser('build', help='build a fresh archive from an SD-root-shaped stage')
    make.add_argument('--stage', type=Path, required=True)
    make.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'verify':
            return report(*verify(args.archive), args.json)
        count, findings, blocked, digest = build(args.stage, args.out)
        return report(count, findings, blocked, args.json, digest)
    except FileExistsError:
        print('RELEASE_ERROR=OUTPUT_EXISTS', file=sys.stderr)
    except ValueError as error:
        print(f'RELEASE_ERROR={error}', file=sys.stderr)
    except OSError:
        print('RELEASE_ERROR=IO', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
