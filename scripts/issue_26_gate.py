#!/usr/bin/env python3
"""Issue 26 private-host inspection helpers. Never execute inspected target files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verified_file(root, relative, expected):
    """Require a digest-reviewed regular input, with no symlink ancestors."""
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('unknown input provenance')
    root = Path(root).absolute()
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('unsafe relative input')
    path = root / relative
    for component in (root, *root.parents, path, *path.parents):
        if component.is_symlink():
            raise ValueError('symlink input or ancestor')
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('input is not regular')
    if sha256(path) != expected:
        raise ValueError('input digest mismatch')
    return path


def clean_environment(workspace):
    """Caller creates private home/tmp/host-bin. No inherited values, including PATH."""
    root = Path(workspace).resolve(strict=True)
    for name in ('home', 'tmp', 'host-bin'):
        p = root / name
        if p.is_symlink() or not p.is_dir():
            raise ValueError('missing or symlink environment directory')
    return {'PATH': str(root / 'host-bin'), 'HOME': str(root / 'home'),
            'TMPDIR': str(root / 'tmp'), 'LC_ALL': 'C', 'LANG': 'C',
            'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '1533081600'}


def verify_tools(records):
    """Verify canonical host binaries before using a separately constructed PATH.

    Records are reviewed local observations, not upstream authenticity proofs.
    No PATH lookup or executable wrapper is accepted here.
    """
    if not isinstance(records, list) or not records:
        raise ValueError('missing tool provenance')
    result = {}
    for item in records:
        if not isinstance(item, dict) or set(item) != {'name', 'path', 'sha256'}:
            raise ValueError('malformed tool record')
        name, path = item['name'], Path(item['path'])
        if not isinstance(name, str) or not re.fullmatch('[a-zA-Z0-9_.+-]+', name):
            raise ValueError('invalid tool name')
        if name in result or not path.is_absolute():
            raise ValueError('duplicate tool or nonabsolute path')
        verified_file(path.parent, path.name, item['sha256'])
        with path.open('rb') as source:
            magic = source.read(2)
        if not os.access(path, os.X_OK) or magic == b'#!':
            raise ValueError('nonexecutable tool or script wrapper')
        result[name] = str(path)
    return result


def verify_search_paths(paths, roots):
    """Use with compiler -v/-H and linker LOAD records, not guessed prefixes."""
    roots = [Path(p).resolve(strict=True) for p in roots]
    if not roots:
        raise ValueError('no reviewed search roots')
    for value in paths:
        p = Path(value)
        if not p.is_absolute() or not any(p.resolve().is_relative_to(r) for r in roots):
            raise ValueError('unreviewed include/library path')


def parse_readelf(text):
    versions, in_needs = set(), False
    for line in text.splitlines():
        if line.startswith('Version needs section'):
            in_needs = True
        elif line.startswith('Version ') and 'section' in line:
            in_needs = False
        if in_needs:
            versions.update(re.findall(r'Name:\s*(\S+)', line))
    interp = re.findall(r'Requesting program interpreter:\s*([^\]]+)\]', text)
    return {'interpreters': interp,
            'needed': re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', text),
            'rpaths': re.findall(r'\((?:RUNPATH|RPATH)\).*?\[([^\]]*)\]', text),
            'versions': sorted(versions),
            'kernel_notes': re.findall(r'OS: Linux, ABI: ([0-9.]+)', text)}


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', value):
        raise ValueError('malformed version')
    parts = tuple(map(int, value.split('.')))
    return parts + (0,) * (3 - len(parts))


def evaluate(facts, policy):
    """A complete experimental policy is required; never asserts H700 readiness."""
    required = {'kernel', 'max_glibc', 'interpreter', 'needed'}
    if not isinstance(policy, dict) or set(policy) != required:
        raise ValueError('incomplete or unknown policy')
    kernel, glibc = version(policy['kernel']), version(policy['max_glibc'])
    if (not isinstance(policy['interpreter'], str) or
            not policy['interpreter'].startswith('/') or
            not isinstance(policy['needed'], list) or
            not policy['needed'] or
            not all(isinstance(x, str) and re.fullmatch(r'[A-Za-z0-9_.+-]+', x)
                    for x in policy['needed']) or
            len(set(policy['needed'])) != len(policy['needed'])):
        raise ValueError('malformed interpreter/NEEDED policy')
    errors = []
    if facts.get('abi') != [64, 'little', 183] or facts.get('type') not in (2, 3):
        errors.append('foreign or nonexecutable ELF ABI')
    if facts['interpreters'] != [policy['interpreter']]:
        errors.append('PT_INTERP mismatch')
    if sorted(facts['needed']) != sorted(policy['needed']):
        errors.append('DT_NEEDED mismatch')
    if facts['rpaths']:
        errors.append('RPATH/RUNPATH forbidden')
    if not facts['kernel_notes'] or any(version(n) > kernel for n in facts['kernel_notes']):
        errors.append('missing/excessive GNU Linux ABI note')
    if not facts['versions']:
        errors.append('missing version-needs evidence')
    for item in facts['versions']:
        if (not re.fullmatch(r'GLIBC_\d+\.\d+(?:\.\d+)?', item) or
                version(item[6:]) > glibc):
            errors.append('unapproved symbol version: ' + item)
    return errors


def inspect_elf(path, expected, readelf_record, workspace, policy):
    path = Path(path).absolute()
    verified_file(path.parent, path.name, expected)
    with path.open('rb') as source:
        data = source.read(64)
    if len(data) < 64 or data[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('invalid/truncated ELF64 little-endian input')
    tool = verify_tools([readelf_record]).get('readelf')
    if not tool:
        raise ValueError('missing native readelf')
    proc = subprocess.run([tool, '--wide', '-h', '-l', '-d', '-V', '-n', str(path)],
                          env=clean_environment(workspace), capture_output=True,
                          text=True, timeout=30, check=False)
    if proc.returncode or proc.stderr:
        raise ValueError('readelf rejected input')
    facts = parse_readelf(proc.stdout)
    facts.update(abi=[64, 'little', struct.unpack_from('<H', data, 18)[0]],
                 type=struct.unpack_from('<H', data, 16)[0])
    errors = evaluate(facts, policy)
    return {'status': 'BLOCKED' if errors else 'PASS_STATIC_EXPERIMENT_ONLY',
            'sha256': expected, 'facts': facts, 'errors': errors,
            'h700_runtime': 'OWNER_NOT_TESTED', 'distribution': 'BLOCKED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('elf', 'sha256', 'readelf-record', 'workspace', 'policy'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        result = inspect_elf(args.elf, args.sha256,
                             json.loads(Path(args.readelf_record).read_text()),
                             args.workspace, json.loads(Path(args.policy).read_text()))
        print(json.dumps(result, indent=2))
        return 2 if result['status'] == 'BLOCKED' else 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'BLOCKED', 'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
