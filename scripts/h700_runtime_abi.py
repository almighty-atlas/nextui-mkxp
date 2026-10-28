#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only, hash-bound H700 ELF candidate closure check. Never runs target ELF.

PASS is static compatibility of an explicit provider graph, NOT an ld.so
simulation: search order, dlopen and runtime binding remain separate evidence.
Only fingerprints/metadata are written to the report, never library bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess


ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
SONAME = re.compile(r'[A-Za-z0-9_.+-]+')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def checked(record):
    require(set(record) == {'path', 'sha256'}, 'INVALID_FILE_RECORD')
    path = Path(record['path'])
    require(path.is_absolute() and path.is_file(), 'MISSING_ABSOLUTE_FILE')
    require(re.fullmatch('[a-f0-9]{64}', record['sha256']) is not None,
            'INVALID_HASH')
    require(digest(path) == record['sha256'], 'HASH_MISMATCH:' + path.name)
    return path.resolve(strict=True)


def parse(text):
    facts = {'needed': [], 'soname': None, 'interpreter': [], 'rpath': [],
             'runpath': [], 'needs': {}, 'definitions': [], 'imports': [],
             'exports': [], 'stack_rw': False, 'textrel': False,
             'copy_relocations': False, 'kernel_notes': []}
    section, provider = None, None
    for line in text.splitlines():
        if line.startswith('Version '):
            section = ('needs' if line.startswith('Version needs section') else
                       'defs' if line.startswith('Version definition section') else None)
            provider = None
        elif line.startswith(('Displaying notes', 'Relocation section', 'Symbol table',
                              'Dynamic section', 'ELF Header', 'Program Headers')):
            section, provider = None, None
        if section == 'needs':
            m = re.search(r'File:\s+(\S+)', line)
            if m:
                provider = m[1]
                facts['needs'].setdefault(provider, [])
            m = re.search(r'^\s*0x[0-9a-f]+:\s+Name:\s*(\S+)', line)
            if m:
                require(provider is not None, 'VERSION_WITHOUT_PROVIDER')
                facts['needs'][provider].append(m[1])
        elif section == 'defs':
            if 'Rev:' in line:
                facts['definitions'].extend(re.findall(r'Name:\s*(\S+)', line))
        m = re.search(r'\(NEEDED\).*?\[([^]]+)\]', line)
        if m:
            facts['needed'].append(m[1])
        m = re.search(r'\(SONAME\).*?\[([^]]+)\]', line)
        if m:
            require(facts['soname'] is None, 'MULTIPLE_SONAME')
            facts['soname'] = m[1]
        for tag in ('RPATH', 'RUNPATH'):
            m = re.search(r'\(' + tag + r'\).*?\[([^]]*)\]', line)
            if m:
                facts[tag.lower()].extend(m[1].split(':'))
        facts['interpreter'].extend(re.findall(
            r'Requesting program interpreter:\s*([^]]+)', line))
        facts['kernel_notes'].extend(re.findall(r'OS: Linux, ABI: ([0-9.]+)', line))
        if re.search(r'GNU_STACK\s+.*\sRW\s', line):
            facts['stack_rw'] = True
        if '(TEXTREL)' in line or re.search(r'\(FLAGS\).*\bTEXTREL\b', line):
            facts['textrel'] = True
        if re.search(r'R_\S+_COPY\b', line):
            facts['copy_relocations'] = True
        # readelf --dyn-syms only; do not mix in the static .symtab.
        m = re.match(r'\s*\d+:\s+[0-9a-f]+\s+\d+\s+\S+\s+'
                     r'(GLOBAL|WEAK|UNIQUE)\s+(DEFAULT|PROTECTED|HIDDEN|INTERNAL)'
                     r'\s+(\S+)\s+(\S+)', line)
        if m:
            bind, visibility, ndx, decorated = m.groups()
            name, separator, version = decorated.partition('@')
            symbol = {'name': name, 'version': version.lstrip('@') or None,
                      'default': not separator or version.startswith('@'),
                      'weak': bind == 'WEAK'}
            if ndx == 'UND':
                facts['imports'].append(symbol)
            elif visibility in ('DEFAULT', 'PROTECTED'):
                facts['exports'].append(symbol)
    return facts


def inspect(path, readelf):
    before = digest(path)
    with path.open('rb') as stream:
        header = stream.read(64)
    require(len(header) == 64 and header[:7] == b'\x7fELF\x02\x01\x01', 'ELF64_LE')
    kind, machine = struct.unpack_from('<HH', header, 16)
    require(machine == 183 and kind in (2, 3), 'AARCH64_EXEC_OR_DYN')
    run = subprocess.run([str(readelf), '-W', '-h', '-l', '-d', '-V',
                          '--dyn-syms', '-r', '-n', str(path)], env=ENV,
                         capture_output=True, text=True, timeout=30)
    require(run.returncode == 0 and not run.stderr and len(run.stdout) < 8 * 1024**2,
            'READELF_FAILED')
    require(digest(path) == before, 'ELF_CHANGED')
    require("Symbol table '.dynsym'" in run.stdout, 'DYNAMIC_SYMBOL_TABLE_MISSING')
    facts = parse(run.stdout)
    facts.update(path=str(path), sha256=before, kind=kind)
    return facts


def new_policy(facts, role):
    issues = []
    expected = ['/lib/ld-linux-aarch64.so.1'] if role == 'program' else []
    if facts['interpreter'] != expected:
        issues.append('INTERPRETER')
    if role != 'program' and facts.get('kind', 3) != 3:
        issues.append('SHARED_OBJECT_TYPE')
    if role == 'program' and not facts['kernel_notes']:
        issues.append('PROGRAM_KERNEL_BASELINE_UNKNOWN')
    for value in facts['kernel_notes']:
        numbers = tuple(map(int, value.split('.')))
        if (numbers + (0, 0, 0))[:3] > (4, 9, 170):
            issues.append('KERNEL_ABOVE_4_9_170')
    if not facts['stack_rw'] or facts['textrel']:
        issues.append('STACK_OR_TEXTREL')
    if facts['rpath'] or any(p != '$ORIGIN' for p in facts['runpath']):
        issues.append('UNREVIEWED_RPATH_RUNPATH')
    if facts['copy_relocations']:
        issues.append('COPY_RELOCATION_REQUIRES_SIZE_AUDIT')
    if any(not SONAME.fullmatch(n) for n in facts['needed']):
        issues.append('NEEDED_NOT_SONAME')
    for versions in facts['needs'].values():
        for version in versions:
            if version == 'GLIBC_PRIVATE':
                issues.append('DIRECT_GLIBC_PRIVATE')
            m = re.fullmatch(r'GLIBC_(\d+)\.(\d+)(?:\.(\d+))?', version)
            if m and tuple(int(x or 0) for x in m.groups()) > (2, 28, 0):
                issues.append('GLIBC_ABOVE_2_28:' + version)
    return issues


def graph_check(roots, objects, providers):
    """Named version definitions plus strong symbol candidates in reachable scope."""
    scope, issues, pending = [], [], list(roots)
    seen = set()
    while pending:
        name = pending.pop(0)
        if name in seen:
            continue
        seen.add(name)
        facts = objects[name]
        scope.append(name)
        for needed in facts['needed']:
            if needed not in providers:
                issues.append('NEEDED_MISSING:' + needed)
            else:
                pending.append(providers[needed])
        for provider, versions in facts['needs'].items():
            if provider not in facts['needed'] or provider not in providers:
                issues.append('VERSION_PROVIDER_MISSING:' + provider)
                continue
            definitions = objects[providers[provider]]['definitions']
            for version in versions:
                if version not in definitions:
                    issues.append('VERSION_MISSING:' + provider + ':' + version)
    exports = {}
    for name in scope:
        for symbol in objects[name]['exports']:
            exports.setdefault(symbol['name'], []).append(symbol)
    count, weak = 0, []
    for name in scope:
        for symbol in objects[name]['imports']:
            matches = exports.get(symbol['name'], [])
            found = any((e['version'] == symbol['version'] if symbol['version']
                         else e['default']) for e in matches)
            if not found:
                label = name + ':' + symbol['name'] + '@' + (symbol['version'] or '')
                if symbol['weak']:
                    weak.append(label)
                else:
                    issues.append('SYMBOL_MISSING:' + label)
            if not symbol['weak']:
                count += 1
    return {'issues': sorted(set(issues)), 'scope': scope,
            'strong_imports': count, 'unresolved_weak': sorted(weak)}


def audit(plan):
    require(type(plan['schema']) is int and plan['schema'] == 1, 'SCHEMA')
    readelf = checked(plan['readelf'])
    with readelf.open('rb') as stream:
        header = stream.read(64)
    require(len(header) == 64 and header[:7] == b'\x7fELF\x02\x01\x01' and
            struct.unpack_from('<H', header, 18)[0] == 62, 'NATIVE_READELF_REQUIRED')
    objects, providers, roles = {}, {}, {}
    require(bool(plan['objects']), 'EMPTY_OBJECT_SET')
    for item in plan['objects']:
        name, role = item['id'], item['role']
        require(name not in objects and role in ('program', 'shared', 'extension', 'stock'),
                'DUPLICATE_ID_OR_INVALID_ROLE')
        facts = inspect(checked(item['file']), readelf)
        objects[name], roles[name] = facts, role
        for alias in item.get('provides', []):
            require(SONAME.fullmatch(alias) and alias not in providers and
                    facts['soname'] == alias, 'PROVIDER_SONAME_OR_DUPLICATE')
            providers[alias] = name
    require('ld-linux-aarch64.so.1' in providers, 'STOCK_LOADER_MISSING')
    require(roles[providers['ld-linux-aarch64.so.1']] == 'stock', 'LOADER_NOT_STOCK')
    result = {'schema': 1, 'status': 'STATIC_ABI_CANDIDATES_PASS', 'objects': {},
              'readelf_sha256': plan['readelf']['sha256'], 'arm_execution': 'NEVER',
              'runtime_binding': 'NOT_VERIFIED', 'distribution': 'BLOCKED'}
    for item in plan['objects']:
        name, role = item['id'], item['role']
        facts = objects[name]
        entry = {key: facts[key] for key in ('sha256', 'needed', 'soname', 'interpreter',
                                            'rpath', 'runpath', 'needs', 'kernel_notes')}
        entry['role'] = role
        entry['issues'] = [] if role == 'stock' else new_policy(facts, role)
        if role != 'stock':
            hosts = item.get('hosts', [])
            require(all(h in objects and roles[h] == 'program' for h in hosts),
                    'INVALID_EMBEDDING_HOST')
            closure = graph_check([*hosts, name], objects, providers)
            entry['issues'] += closure.pop('issues')
            entry.update(closure)
        if entry['issues']:
            result['status'] = 'STATIC_ABI_FAIL'
        result['objects'][name] = entry
    # Detect mutation after cached inspection, including providers and tooling.
    checked(plan['readelf'])
    for item in plan['objects']:
        checked(item['file'])
    return result


def relocatables(root, readelf):
    """Inspect intermediate objects and archive members without linking/running."""
    count, archives = 0, {}
    for path in sorted(root.rglob('*.o')):
        require(not path.is_symlink(), 'OBJECT_SYMLINK')
        with path.open('rb') as stream:
            h = stream.read(64)
        require(len(h) == 64 and h[:7] == b'\x7fELF\x02\x01\x01' and
                struct.unpack_from('<HH', h, 16) == (1, 183), 'NOT_AARCH64_REL:' + path.name)
        count += 1
    for path in sorted(root.rglob('*.a')):
        if path.is_symlink():
            require(path.resolve().is_relative_to(root.resolve()), 'ARCHIVE_LINK_ESCAPE')
            continue
        before = digest(path)
        result = subprocess.run([str(readelf), '-W', '-h', str(path)], env=ENV,
                                capture_output=True, text=True, timeout=30)
        require(result.returncode == 0 and not result.stderr and digest(path) == before,
                'ARCHIVE_INSPECTION_FAILED')
        machines = re.findall(r'^\s*Machine:\s*(.+)$', result.stdout, re.M)
        kinds = re.findall(r'^\s*Type:\s*(.+)$', result.stdout, re.M)
        classes = re.findall(r'^\s*Class:\s*(.+)$', result.stdout, re.M)
        require(machines and all(m == 'AArch64' for m in machines) and
                len(machines) == len(kinds) == len(classes) and
                all(k.startswith('REL ') for k in kinds) and all(c == 'ELF64' for c in classes),
                'NON_AARCH64_ARCHIVE_MEMBER')
        archives[path.relative_to(root).as_posix()] = {'sha256': before, 'members': len(machines)}
    return {'status': 'AARCH64_INTERMEDIATES_PASS', 'objects': count, 'archives': archives}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--extensions-dir', type=Path)
    parser.add_argument('--helpers-dir', type=Path)
    parser.add_argument('--relocatable-tree', type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text())
        if args.extensions_dir:
            add_outputs(plan, args.extensions_dir, args.helpers_dir)
        else:
            require(args.helpers_dir is None, 'HELPERS_REQUIRE_EXTENSIONS_DIR')
        result = audit(plan)
        if args.relocatable_tree:
            result['intermediates'] = relocatables(args.relocatable_tree.resolve(strict=True),
                                                   checked(plan['readelf']))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        result = {'status': 'STATIC_ABI_BLOCKED', 'reason': str(error),
                  'arm_execution': 'NEVER', 'distribution': 'BLOCKED'}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'STATIC_ABI_CANDIDATES_PASS' else 2


def add_outputs(plan, extensions, helpers=None):
    """Inventory every final .so and libffi helper DSO; hash-bind in-memory plan."""
    extensions = extensions.resolve(strict=True)
    require(extensions.is_dir(), 'EXTENSION_DIRECTORY')
    known = {item['file']['sha256'] for item in plan['objects']}
    paths = [(p, p.relative_to(extensions).as_posix(), 'extension')
             for p in sorted(extensions.rglob('*.so'))]
    if helpers:
        paths += [(p, 'helper/' + p.name, 'shared')
                  for p in sorted(helpers.resolve(strict=True).rglob('*.so.*'))]
    for path, name, role in paths:
        if path.is_symlink():
            require(path.resolve().is_relative_to(path.parents[2]), 'OUTPUT_LINK_ESCAPE')
            continue
        h = digest(path)
        if h in known:
            continue
        plan['objects'].append({'id': name, 'role': role, 'provides': [],
                                'file': {'path': str(path), 'sha256': h}})
        known.add(h)


if __name__ == '__main__':
    raise SystemExit(main())
