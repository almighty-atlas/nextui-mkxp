#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline C++ calibration gates. Only native mode can execute a built probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'spikes/h700-cxx-abi/probe.cpp'
RESERVE = 20 * 1024**3
COMPILER_ARCHIVE_HASH = 'd4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3'
PROVIDERS = {
    'libstdc++.so.6.0.25': '678f07e10eecaced61f0686af119680fc6d0a23487b057cc3be5718204716fa4',
    'libgcc_s.so.1': '3e250c02603da82479e64559d926bae3964e6ea6128f1c74dc8339bfb97fe476',
}
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'TZ': 'UTC'}


class Blocked(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Blocked(code)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def elf_header(path, machine, types):
    with Path(path).open('rb') as stream:
        header = stream.read(64)
    require(len(header) == 64 and header[:7] == b'\x7fELF\x02\x01\x01', 'ELF_HEADER')
    kind, arch = struct.unpack_from('<HH', header, 16)
    require(arch == machine and kind in types, 'ELF_MACHINE_OR_TYPE')
    return kind


def reserve(path):
    require(shutil.disk_usage(path).free >= RESERVE, 'FREE_SPACE_BELOW_20_GIB')


def native(workspace, compiler=None):
    # Explicit caller-selected trusted native OS compiler, never a cross compiler.
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64',
            'NATIVE_HOST_UNSUPPORTED')
    selected = compiler or shutil.which('c++') or shutil.which('g++')
    require(selected is not None, 'NATIVE_CXX_COMPILER_UNAVAILABLE')
    selected = Path(selected).resolve(strict=True)
    elf_header(selected, 62, {2, 3})  # Refuse scripts and AArch64 compiler binaries.
    compiler_digest = sha(selected)
    workspace = Path(workspace).absolute()
    require(workspace.parent.is_dir() and not workspace.exists() and
            not workspace.is_symlink() and not workspace.resolve().is_relative_to(ROOT),
            'FRESH_PRIVATE_WORKSPACE_REQUIRED')
    reserve(workspace.parent)
    workspace.mkdir(mode=0o700)
    (workspace/'tmp').mkdir(mode=0o700)
    env = dict(ENV, TMPDIR=str(workspace/'tmp'))  # No inherited LD_*, CPATH, etc.
    binary = workspace/'probe-native'
    command = [str(selected), '-std=c++14', '-O0', '-Wall', '-Wextra', '-Werror',
               str(SOURCE), '-o', str(binary)]
    build = subprocess.run(command, cwd=workspace, env=env, capture_output=True,
                           timeout=60)
    (workspace/'compile.stdout').write_bytes(build.stdout)
    (workspace/'compile.stderr').write_bytes(build.stderr)
    require(build.returncode == 0, 'NATIVE_COMPILE_FAILED')
    require(sha(selected) == compiler_digest, 'NATIVE_COMPILER_CHANGED')
    reserve(workspace)
    elf_header(binary, 62, {2, 3})  # This is the ONLY generated file ever executed.
    run = subprocess.run([str(binary)], cwd=workspace, env=env, capture_output=True,
                         timeout=10)
    require(run.returncode == 0 and run.stderr == b'' and run.stdout ==
            b'RMXP_CXX14 native_or_target_probe_ok destructors=2\n', 'NATIVE_PROBE_FAILED')
    result = {'status': 'NATIVE_HOST_PASS', 'source_sha256': sha(SOURCE),
              'compiler_sha256': compiler_digest, 'native_elf_sha256': sha(binary),
              'destructors': 2, 'arm_execution': 'NEVER', 'distribution': 'BLOCKED'}
    (workspace/'native-result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def within(path, roots):
    path = Path(path)
    require(path.is_absolute(), 'NONABSOLUTE_SEARCH_PATH')
    resolved = path.resolve(strict=True)
    require(any(resolved.is_relative_to(Path(root).resolve(strict=True))
                for root in roots), 'UNREVIEWED_SEARCH_PATH')
    return resolved


def search_audit(includes, libraries, startups, *, compiler_headers, sysroot,
                 compiler_runtime, cxx_library_dir, old_sdk):
    """Audit observed paths, not guessed default flags. No compile/link here."""
    require(bool(includes) and bool(libraries) and bool(startups), 'MISSING_SEARCH_EVIDENCE')
    old = Path(old_sdk).resolve(strict=True)
    for values, roots in ((includes, [*compiler_headers, Path(sysroot)/'usr/include']),
                          (libraries, [Path(sysroot)/'lib64', Path(sysroot)/'usr/lib64',
                                       compiler_runtime, cxx_library_dir]),
                          (startups, [Path(sysroot)/'usr/lib64', compiler_runtime])):
        for value in values:
            resolved = within(value, roots)
            require(not resolved.is_relative_to(old), 'OLD_SDK_INPUT')
    required = {'crt1.o', 'crti.o', 'crtn.o', 'crtbegin.o', 'crtend.o'}
    require({Path(p).name for p in startups} == required and len(startups) == 5,
            'STARTUP_SET')
    for value in startups:
        path = Path(value).resolve(strict=True)
        root = compiler_runtime if path.name.startswith(('crtbegin', 'crtend')) else Path(sysroot)/'usr/lib64'
        within(path, [root])
    return {'status': 'SEARCH_PATH_AUDIT_ONLY', 'cross_link_performed': False}


def parse_readelf(text):
    needs = {}
    definitions = set()
    section, provider = None, None
    for line in text.splitlines():
        if line.startswith('Version '):
            section = 'needs' if line.startswith('Version needs section') else (
                'definitions' if line.startswith('Version definition section') else None)
            provider = None
        if section == 'needs':
            match = re.search(r'File:\s+(\S+)', line)
            if match:
                provider = match[1]
                needs.setdefault(provider, set())
            for name in re.findall(r'Name:\s*(\S+)', line):
                require(provider is not None, 'VERSION_PROVIDER_MISSING')
                needs[provider].add(name)
        elif section == 'definitions':
            definitions.update(re.findall(r'Name:\s*(\S+)', line))
    return {
        'interpreters': re.findall(r'Requesting program interpreter:\s*([^\]]+)', text),
        'kernel_notes': re.findall(r'OS: Linux, ABI: ([0-9.]+)', text),
        'needed': re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', text),
        'sonames': re.findall(r'\(SONAME\).*?\[([^\]]+)\]', text),
        'rpaths': re.findall(r'\((?:RPATH|RUNPATH)\).*?\[([^\]]*)\]', text),
        'textrel': bool(re.search(r'\(TEXTREL\)', text)),
        'nonexec_stack': bool(re.search(r'GNU_STACK\s+[^\n]*\sRW\s', text)),
        'needs': {p: sorted(v) for p, v in sorted(needs.items())},
        'definitions': sorted(definitions),
    }


def elf_policy(facts, provider_definitions):
    require(facts['interpreters'] == ['/lib/ld-linux-aarch64.so.1'], 'INTERPRETER')
    require(facts['kernel_notes'] == ['4.9.0'], 'KERNEL_ABI')
    require(not facts['rpaths'] and not facts['textrel'] and facts['nonexec_stack'],
            'ELF_PATH_STACK_OR_TEXTREL')
    allowed = {'libstdc++.so.6', 'libgcc_s.so.1', 'libm.so.6', 'libc.so.6'}
    require({'libstdc++.so.6', 'libgcc_s.so.1', 'libc.so.6'} <= set(facts['needed'])
            <= allowed and len(facts['needed']) == len(set(facts['needed'])), 'NEEDED')
    all_versions = set()
    for provider, versions in facts['needs'].items():
        require(provider in allowed and provider in facts['needed'] and provider in provider_definitions and
                versions and set(versions) <= set(provider_definitions[provider]),
                'UNRESOLVED_VERSION_PROVIDER')
        for version in versions:
            require(re.fullmatch(r'(?:GLIBC|GLIBCXX|CXXABI|GCC)_\d+(?:\.\d+){1,2}', version),
                    'UNREVIEWED_VERSION')
            if version.startswith('GLIBC_'):
                numbers = tuple(map(int, version[6:].split('.')))
                require(numbers + (0,) * (3-len(numbers)) <= (2, 28, 0), 'GLIBC_FLOOR')
            elif version.startswith(('GLIBCXX_', 'CXXABI_')):
                require(provider == 'libstdc++.so.6', 'VERSION_NAMESPACE_PROVIDER')
            else:
                require(provider == 'libgcc_s.so.1', 'VERSION_NAMESPACE_PROVIDER')
        all_versions.update(versions)
    require(all(any(v.startswith(prefix) for v in all_versions)
                for prefix in ('GLIBC_', 'GLIBCXX_', 'CXXABI_')), 'MISSING_CXX_VERSIONS')
    return {'status': 'ELF_POLICY_ONLY', 'h700_runtime': 'NOT_TESTED'}


def checked_record(record):
    require(isinstance(record, dict) and set(record) == {'path', 'sha256'} and
            isinstance(record['path'], str) and Path(record['path']).is_absolute() and
            isinstance(record['sha256'], str) and
            re.fullmatch('[0-9a-f]{64}', record['sha256']), 'LOCAL_RECEIPT_OR_INPUT_REQUIRED')
    path = Path(record['path'])
    require(path.is_file() and sha(path) == record['sha256'], 'LOCAL_INPUT_HASH')
    return path.resolve(strict=True)


def tree_digest(root):
    # Same content/link algorithm as the pinned PR #27 helper, not an archive hash.
    root = Path(root).resolve(strict=True)
    items = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '.git' in relative.parts:
            continue
        if path.is_symlink():
            require(path.resolve().is_relative_to(root), 'TREE_LINK_ESCAPE')
            items.append((relative.as_posix(), 'link', str(path.readlink())))
        elif path.is_file():
            items.append((relative.as_posix(), 'file', sha(path)))
    return hashlib.sha256(json.dumps(items, separators=(',', ':')).encode()).hexdigest()


def cross_audit(plan):
    """Read-only receipt/search snapshot audit. It NEVER authorizes/runs a link."""
    require(isinstance(plan, dict) and type(plan.get('schema')) is int and
            plan.get('schema') == 1 and plan.get('scope') == 'private-cxx14-calibration',
            'CALIBRATION_SCOPE')
    require(plan.get('source_sha256') == sha(SOURCE), 'PROBE_SOURCE_HASH')
    lock_path = checked_record(plan['receipts']['input_lock'])
    sysroot_path = checked_record(plan['receipts']['sysroot'])
    sdl_path = checked_record(plan['receipts']['sdl'])
    lock = json.loads(lock_path.read_text())
    receipt = json.loads(sysroot_path.read_text())
    sdl = json.loads(sdl_path.read_text())
    require(receipt.get('source_lock_sha256') == sha(lock_path), 'LOCK_RECEIPT_MISMATCH')
    compiler_hash = COMPILER_ARCHIVE_HASH
    require(lock['compiler']['sha256'] == compiler_hash, 'COMPILER_LOCK')
    require(plan['compiler_archive']['sha256'] == compiler_hash, 'COMPILER_LOCK')
    checked_record(plan['compiler_archive'])
    sysroot = Path(plan['sysroot']).resolve(strict=True)
    reserve(sysroot)
    compiler = Path(plan['compiler_root']).resolve(strict=True)
    require(receipt.get('sysroot_tree_sha256') == tree_digest(sysroot), 'SYSROOT_TREE')
    require(plan.get('reviewed_compiler_tree_sha256') == tree_digest(compiler), 'COMPILER_TREE')
    require(sdl.get('status') == 'SDL_ONLY_HOST_LINKED' and
            sdl.get('sysroot_tree') == receipt['sysroot_tree_sha256'], 'SDL_RECEIPT_MISMATCH')
    require(receipt.get('target_execution') == 'NEVER' and
            receipt.get('distribution') == 'BLOCKED', 'RECEIPT_SCOPE')
    for name, expected in PROVIDERS.items():
        require(plan['providers'][name]['sha256'] == expected, 'PROVIDER_EXPECTED_HASH')
        path = checked_record(plan['providers'][name])
        within(path, [compiler])
        elf_header(path, 183, {3})
    roots = {'compiler_headers': plan['compiler_headers'], 'sysroot': sysroot,
             'compiler_runtime': plan['compiler_runtime'],
             'cxx_library_dir': plan['cxx_library_dir'], 'old_sdk': plan['old_sdk']}
    # Don't bless arbitrary host directories just because they were listed in a plan.
    for path in [*roots['compiler_headers'], roots['compiler_runtime'], roots['cxx_library_dir']]:
        within(path, [compiler])
    for name in ('includes', 'libraries', 'startups'):
        require(isinstance(plan[name], list), 'MISSING_SEARCH_EVIDENCE')
    search_audit(plan['includes'], plan['libraries'], plan['startups'], **roots)
    # Every concrete startup input must also have a reviewed, matching file hash.
    require(set(plan['startup_records']) == set(plan['startups']), 'STARTUP_RECEIPTS')
    for path, expected in plan['startup_records'].items():
        checked_record({'path': path, 'sha256': expected})
        elf_header(path, 183, {1})
    return {'status': 'CROSS_INPUT_AUDIT_ONLY', 'cross_link_performed': False,
            'search_snapshot_origin': 'CALLER_REVIEWED_NOT_COMPILER_ATTESTATION',
            'complete_link_input_closure': 'NOT_CHECKED', 'arm_execution': 'NEVER',
            'distribution': 'BLOCKED'}


def audit_link_map(text, records, old_sdk):
    """Every actual LOAD must be an explicitly fingerprinted, resolved file."""
    paths = re.findall(r'^LOAD (.+)$', text, re.M)
    require(bool(paths), 'EMPTY_LINK_MAP')
    old = Path(old_sdk).resolve(strict=True)
    for value in paths:
        path = Path(value)
        require(path.is_absolute(), 'RELATIVE_MAP_INPUT')
        require(not path.resolve(strict=True).is_relative_to(old), 'OLD_SDK_INPUT')
        require(value in records, 'UNKNOWN_MAP_INPUT')
        checked_record({'path': value, 'sha256': records[value]})
    return {'status': 'LINK_MAP_LOAD_AUDIT_ONLY', 'load_records': len(paths),
            'archive_member_and_symbol_closure': 'NOT_CHECKED',
            'arm_execution': 'NEVER', 'distribution': 'BLOCKED'}


def inspect(binary, readelf, readelf_sha256):
    readelf = Path(readelf).resolve(strict=True)
    require(isinstance(readelf_sha256, str) and
            re.fullmatch('[0-9a-f]{64}', readelf_sha256) and
            sha(readelf) == readelf_sha256, 'READELF_HASH')
    elf_header(readelf, 62, {2, 3})
    binary = Path(binary)
    require(binary.is_file() and not binary.is_symlink() and
            64 <= binary.stat().st_size <= 16 * 1024**2, 'BOUNDED_REGULAR_ELF')
    elf_header(binary, 183, {2, 3})
    before = sha(binary)
    result = subprocess.run([str(readelf), '-W', '-h', '-l', '-d', '-V', '-n',
                             str(binary)], env=ENV, capture_output=True, text=True,
                            timeout=30)
    require(result.returncode == 0 and not result.stderr and
            len(result.stdout) <= 4 * 1024**2, 'READELF_FAILED')
    require(sha(binary) == before, 'ELF_CHANGED')
    return {'status': 'ELF_FACTS_ONLY', 'sha256': before, 'machine': 'AArch64',
            'facts': parse_readelf(result.stdout),
            'policy': 'NOT_EVALUATED', 'link_input_provenance': 'NOT_CHECKED',
            'arm_execution': 'NEVER', 'distribution': 'BLOCKED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    host = commands.add_parser('native')
    host.add_argument('--workspace', type=Path, required=True)
    host.add_argument('--compiler', type=Path)
    target = commands.add_parser('inspect')
    target.add_argument('--elf', type=Path, required=True)
    target.add_argument('--readelf', type=Path, required=True)
    target.add_argument('--readelf-sha256', required=True)
    audit = commands.add_parser('cross-audit')
    audit.add_argument('--plan', type=Path, required=True)
    commands.add_parser('cross-status')
    args = parser.parse_args()
    try:
        if args.command == 'native':
            result = native(args.workspace, args.compiler)
        elif args.command == 'inspect':
            result = inspect(args.elf, args.readelf, args.readelf_sha256)
        elif args.command == 'cross-audit':
            result = cross_audit(json.loads(args.plan.read_text()))
        else:
            result = {'status': 'CROSS_BUILD_BLOCKED', 'arm_execution': 'NEVER',
                      'reasons': ['TINY02_LOCAL_INPUT_PATHS_AND_RAW_RECEIPTS_UNAVAILABLE',
                                  'PRELINK_SEARCH_TRANSCRIPTS_AND_LINK_INPUT_INVENTORY_UNAVAILABLE'],
                      'distribution': 'BLOCKED'}
    except Blocked as error:
        result = {'status': 'HOST_BUILD_BLOCKED' if args.command == 'native' else 'CROSS_BUILD_BLOCKED',
                  'reason': str(error), 'distribution': 'BLOCKED', 'arm_execution': 'NEVER'}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        result = {'status': 'HOST_BUILD_BLOCKED' if args.command == 'native' else 'CROSS_BUILD_BLOCKED',
                  'reason': 'MISSING_OR_INVALID_LOCAL_INPUT_OR_TOOL',
                  'distribution': 'BLOCKED', 'arm_execution': 'NEVER'}
    print(json.dumps(result, sort_keys=True))
    return 2 if result['status'].endswith('BLOCKED') else 0


if __name__ == '__main__':
    raise SystemExit(main())
