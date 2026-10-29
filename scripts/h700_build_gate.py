#!/usr/bin/env python3
"""Offline archive/ELF checks for issue #24. Never executes an inspected target."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import tarfile


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    if not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('expected lowercase SHA256')
    return value


def member_path(name):
    if not name or '\\' in name or '\x00' in name:
        raise ValueError('invalid archive path')
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('absolute/traversing archive path: ' + name)
    return p


def link_target(path, target, hard=False):
    if not target or '\\' in target or PurePosixPath(target).is_absolute():
        raise ValueError('absolute/invalid link: ' + str(path))
    parts = list(() if hard else path.parent.parts)
    for part in PurePosixPath(target).parts:
        if part == '..':
            if not parts:
                raise ValueError('escaping link: ' + str(path))
            parts.pop()
        elif part != '.':
            parts.append(part)
    return PurePosixPath(*parts)


def archive_members(archive, expected, prefixes=None):
    """Verify bytes BEFORE parsing; reject special files and symlink ancestors."""
    if sha256(archive) != digest(expected):
        raise ValueError('SHA256 mismatch')
    with tarfile.open(archive, 'r:*') as tar:
        members = tar.getmembers()
    if len(members) > 200000 or sum(m.size for m in members if m.isfile()) > 4*1024**3:
        raise ValueError("archive exceeds member/data limits")
    selected = [member_path(x) for x in prefixes or []]
    paths = {}
    for m in members:
        p = member_path(m.name)
        if str(p) == '.':
            if not m.isdir():
                raise ValueError('non-directory root')
            continue
        if selected and not any(p == prefix or prefix in p.parents for prefix in selected):
            continue
        if p in paths:
            raise ValueError('duplicate archive path: ' + str(p))
        if not (m.isfile() or m.isdir() or m.issym() or m.islnk()):
            raise ValueError('special archive file: ' + str(p))
        if m.issym() or m.islnk():
            link_target(p, m.linkname, m.islnk())
        paths[p] = m
    for p in paths:
        for parent in p.parents:
            if parent in paths and not paths[parent].isdir():
                raise ValueError('non-directory ancestor: ' + str(parent))
    for p, m in paths.items():
        if m.islnk():
            target = paths.get(link_target(p, m.linkname, True))
            if target is None or not target.isfile():
                raise ValueError('hardlink target is not regular: ' + str(p))
    return paths


def safe_extract(archive, expected, destination, prefixes=None):
    paths = archive_members(archive, expected, prefixes)
    dest = Path(destination)
    if dest.exists() or dest.is_symlink():
        raise ValueError('destination must not already exist')
    # Preflight complete before any writes. No extractall, ownership, device or
    # privileged mode restoration. Links created LAST, never followed to write.
    dest.mkdir(parents=True)
    with tarfile.open(archive, 'r:*') as tar:
        for p, m in paths.items():
            out = dest / str(p)
            if m.isdir():
                out.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                out.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(m) as source, out.open('xb') as target:
                    shutil.copyfileobj(source, target)
                out.chmod(m.mode & 0o755)
        for p, m in paths.items():
            out = dest / str(p)
            if m.issym() or m.islnk():
                out.parent.mkdir(parents=True, exist_ok=True)
                if m.issym():
                    out.symlink_to(m.linkname)
                else:
                    shutil.copyfile(dest / str(link_target(p, m.linkname, True)), out)
    return {'members': len(paths), 'sha256': expected}


def version_tuple(version):
    parts = [int(x) for x in version.split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def parse_readelf(text):
    interp = re.search(r'Requesting program interpreter:\s*([^\]]+)\]', text)
    needs = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', text)
    paths = re.findall(r'\((?:RUNPATH|RPATH)\).*?\[([^\]]*)\]', text)
    in_needs = False
    versions = set()
    for line in text.splitlines():
        if line.startswith('Version needs section'):
            in_needs = True
        elif line.startswith('Version ') and 'section' in line:
            in_needs = False
        if in_needs:
            versions.update(re.findall(r'Name:\s*(\S+)', line))
    return {'interpreter': interp.group(1).strip() if interp else None,
            'needed': sorted(set(needs)), 'rpaths': paths,
            'required_versions': sorted(versions),
            'gnu_linux_abi': (re.search(r'OS: Linux, ABI: ([0-9.]+)', text).group(1)
                              if re.search(r'OS: Linux, ABI: ([0-9.]+)', text) else None)}


def evaluate(facts, policy):
    for key in ('allowed_needed', 'allowed_rpaths', 'allowed_other_versions'):
        if policy.get(key) is not None and (not isinstance(policy[key], list) or
                not all(isinstance(x, str) and x for x in policy[key])):
            raise ValueError('invalid policy list: ' + key)
    for key in ('max_glibc', 'kernel'):
        if policy.get(key) is not None and (not isinstance(policy[key], str) or
                not re.fullmatch(r'[0-9]+(?:\.[0-9]+)+', policy[key])):
            raise ValueError('invalid policy version: ' + key)
    if policy.get('interpreter') is not None and (not isinstance(policy['interpreter'], str)
                                                 or not policy['interpreter'].startswith('/')):
        raise ValueError('invalid interpreter policy')
    errors = []
    if facts.get('class') != 64 or facts.get('endian') != 'little' or facts.get('machine') != 183:
        errors.append('not ELF64 little-endian AArch64')
    if facts.get('type') not in (2, 3):
        errors.append('not an executable/PIE ELF type')
    for key in ('interpreter', 'allowed_needed', 'max_glibc', 'allowed_rpaths', 'kernel'):
        if policy.get(key) is None:
            errors.append('UNKNOWN target policy: ' + key)
    if policy.get('kernel') is not None:
        if not facts.get('gnu_linux_abi'):
            errors.append('UNKNOWN GNU Linux ABI note')
        elif version_tuple(facts['gnu_linux_abi']) > version_tuple(policy['kernel']):
            errors.append('GNU Linux ABI note exceeds observed kernel')
    if policy.get('interpreter') is not None and facts.get('interpreter') != policy['interpreter']:
        errors.append('interpreter mismatch')
    if policy.get('allowed_needed') is not None:
        for lib in facts['needed']:
            if lib not in policy['allowed_needed']:
                errors.append('unexpected NEEDED: ' + lib)
    if policy.get('allowed_rpaths') is not None:
        for path in facts['rpaths']:
            if path not in policy['allowed_rpaths']:
                errors.append('unexpected RPATH/RUNPATH')
    for version in facts['required_versions']:
        if version.startswith('GLIBC_'):
            number = version.removeprefix('GLIBC_')
            if not re.fullmatch(r'\d+(?:\.\d+)+', number):
                errors.append('unreviewed GLIBC version: ' + version)
            elif policy.get('max_glibc') is not None and version_tuple(number) > version_tuple(policy['max_glibc']):
                errors.append('GLIBC requirement above approved floor: ' + version)
        elif version.startswith('GLIBCXX_') or version.startswith('CXXABI_'):
            errors.append('unexpected C++ runtime requirement: ' + version)
        elif version not in policy.get('allowed_other_versions', []):
            errors.append('unreviewed symbol version: ' + version)
    return errors


def scan_elf(path, policy):
    path = Path(path)
    if not path.is_file():
        raise ValueError('input is not a regular file')
    with path.open('rb') as source:
        head = source.read(20)
    if len(head) != 20 or head[:4] != b'\x7fELF' or head[4] not in (1, 2) or head[5] not in (1, 2):
        raise ValueError('invalid/truncated ELF header')
    order = '<' if head[5] == 1 else '>'
    result = subprocess.run(['readelf', '--wide', '--file-header', '--program-headers',
                             '--dynamic', '--version-info', '--notes', str(path.resolve())],
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError('readelf failed')
    facts = parse_readelf(result.stdout)
    facts.update({'sha256': sha256(path), 'class': 64 if head[4] == 2 else 32,
                  'endian': 'little' if head[5] == 1 else 'big',
                  'type': struct.unpack(order + 'H', head[16:18])[0],
                  'machine': struct.unpack(order + 'H', head[18:20])[0]})
    errors = evaluate(facts, policy)
    return {'status': 'BLOCKED' if errors else 'STATIC_POLICY_MATCH_ONLY',
            'facts': facts, 'errors': errors,
            'limitation': 'No execution; no dlopen closure, rights or H700 runtime approval'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'extract'):
        sub = commands.add_parser(name)
        sub.add_argument('archive'); sub.add_argument('--sha256', required=True, type=digest)
        sub.add_argument('--prefix', action='append', default=[], help='Explicit member/subtree selection; excluded members never extracted')
        if name == 'extract': sub.add_argument('destination')
    elf = commands.add_parser('elf')
    elf.add_argument('file'); elf.add_argument('--policy', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            members = archive_members(args.archive, args.sha256, args.prefix)
            result = {'sha256': args.sha256, 'members': len(members),
                      'links': sum(m.issym() or m.islnk() for m in members.values())}
        elif args.command == 'extract':
            result = safe_extract(args.archive, args.sha256, args.destination, args.prefix)
        else:
            result = scan_elf(args.file, json.loads(Path(args.policy).read_text()))
        print(json.dumps(result, indent=2))
        return 2 if result.get('status') == 'BLOCKED' else 0
    except (ValueError, OSError, tarfile.TarError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
