#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive a hash-bound source lock from a pinned mkxp-z checkout's Meson wraps.

Only selected wraps are locked; every other wrap must be explicitly excluded
so upstream additions cannot slip in. --fetch downloads HTTPS archives into a
private Meson packagecache and verifies each SHA-256; nothing is extracted,
configured or executed. A complete lock is not a license or build approval.
"""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

from h700_cxx_abi import tree_digest


HEX40 = re.compile(r'[0-9a-f]{40}')
HEX64 = re.compile(r'[0-9a-f]{64}')
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'GIT_TERMINAL_PROMPT': '0'}
MAX_ARCHIVE = 256 * 1024**2


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_wrap(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(Path(path).read_text())
    kinds = [s for s in parser.sections() if s.startswith('wrap-')]
    require(len(kinds) == 1, 'WRAP_SECTION:' + Path(path).name)
    fields = dict(parser[kinds[0]])
    diff = fields.pop('diff_files', '')
    fields['diff_files'] = [d.strip() for d in diff.replace('\n', ',').split(',') if d.strip()]
    return kinds[0], fields


def git(args, cwd=None, timeout=600):
    run = subprocess.run(['git', *args], cwd=cwd, env=ENV, capture_output=True,
                         text=True, timeout=timeout)
    require(run.returncode == 0,
            'GIT_FAILED:' + ' '.join(args[:2]) + ':' + run.stderr.strip()[-200:])
    return run.stdout


def lock(source, profile):
    source = Path(source).resolve(strict=True)
    if (source / '.git').exists():
        require(git(['rev-parse', 'HEAD'], cwd=source).strip() == profile['commit'],
                'ENGINE_COMMIT_MISMATCH')
    subprojects = source / 'subprojects'
    packagefiles = subprojects / 'packagefiles'
    available = {p.stem for p in subprojects.glob('*.wrap')}
    selected, excluded = set(profile['wraps']), set(profile['excluded_wraps'])
    issues = ['UNCLASSIFIED_WRAP:' + n for n in sorted(available - selected - excluded)]
    issues += ['SELECTED_AND_EXCLUDED:' + n for n in sorted(selected & excluded)]
    issues += ['STALE_EXCLUSION:' + n for n in sorted(excluded - available)]
    entries = {}
    for name in sorted(selected):
        path = subprojects / (name + '.wrap')
        if not path.is_file():
            issues.append('WRAP_MISSING:' + name)
            continue
        kind, fields = parse_wrap(path)
        entry = {'kind': kind, 'wrap_sha256': sha(path),
                 'directory': fields.get('directory', name)}
        if kind == 'wrap-file':
            urls = [fields.get('source_url', '')]
            if 'source_fallback_url' in fields:
                urls.append(fields['source_fallback_url'])
            entry.update(urls=urls, sha256=fields.get('source_hash'),
                         filename=fields.get('source_filename') or urls[0].rsplit('/', 1)[-1])
            if not HEX64.fullmatch(entry['sha256'] or ''):
                issues.append('ARCHIVE_HASH_MISSING:' + name)
            if not all(u.startswith('https://') for u in urls):
                issues.append('NON_HTTPS_URL:' + name)
        elif kind == 'wrap-git':
            pin = profile.get('git_pins', {}).get(name, {})
            entry.update(url=fields.get('url', ''), revision=fields.get('revision', ''),
                         recursive=fields.get('clone-recursive') == 'true',
                         commit=pin.get('commit'), submodules=pin.get('submodules'))
            if not HEX40.fullmatch(entry['commit'] or ''):
                issues.append('MUTABLE_GIT_REVISION:' + name)
            if entry['recursive'] and not entry['submodules']:
                issues.append('SUBMODULES_UNRECORDED:' + name)
            if not entry['url'].startswith('https://'):
                issues.append('NON_HTTPS_URL:' + name)
        else:
            issues.append('UNSUPPORTED_WRAP_KIND:' + name)
        if 'patch_directory' in fields:
            directory = packagefiles / fields['patch_directory']
            if directory.is_dir():
                entry['patch_directory_tree_sha256'] = tree_digest(directory)
            else:
                issues.append('PATCH_DIRECTORY_MISSING:' + name)
        entry['diff_files'] = {}
        for diff in fields['diff_files']:
            p = packagefiles / diff
            if p.is_file():
                entry['diff_files'][diff] = sha(p)
            else:
                issues.append('DIFF_FILE_MISSING:' + name + ':' + diff)
        entries[name] = entry
    return {'schema': 1, 'engine': 'mkxp-z', 'commit': profile['commit'],
            'status': 'LOCK_COMPLETE' if not issues else 'LOCK_INCOMPLETE',
            'issues': issues, 'wraps': entries, 'excluded_wraps': sorted(excluded),
            'license_review': 'NOT_PERFORMED', 'distribution': 'BLOCKED'}


def download(urls, expected, destination):
    """HTTPS only, bounded size, verified before the atomic rename."""
    if destination.exists():
        require(sha(destination) == expected, 'CACHED_ARCHIVE_HASH_MISMATCH:' + destination.name)
        return 'CACHED'
    errors = []
    for url in urls:
        require(url.startswith('https://'), 'NON_HTTPS_URL')
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as tmp:
            part = Path(tmp.name)
        try:
            h, size = hashlib.sha256(), 0
            with urllib.request.urlopen(url, timeout=60) as response, part.open('wb') as out:
                require(response.geturl().startswith('https://'), 'REDIRECT_NOT_HTTPS')
                for chunk in iter(lambda: response.read(1024 * 1024), b''):
                    size += len(chunk)
                    require(size <= MAX_ARCHIVE, 'ARCHIVE_TOO_LARGE')
                    h.update(chunk)
                    out.write(chunk)
            require(h.hexdigest() == expected, 'DOWNLOAD_HASH_MISMATCH')
            part.rename(destination)
            return 'DOWNLOADED'
        except (OSError, ValueError) as error:
            errors.append(str(error)[:120])
        finally:
            part.unlink(missing_ok=True)
    raise ValueError('DOWNLOAD_FAILED:' + destination.name + ':' + ';'.join(errors))


def clone(entry, destination):
    """Shallow recursive clone at an immutable commit; record submodule commits."""
    require(not destination.exists(), 'GIT_DESTINATION_EXISTS:' + destination.name)
    require(HEX40.fullmatch(entry['commit'] or ''), 'MUTABLE_GIT_REVISION')
    destination.mkdir(parents=True)
    git(['init', '-q'], cwd=destination)
    git(['fetch', '-q', '--depth', '1', entry['url'], entry['commit']], cwd=destination)
    git(['checkout', '-q', '--detach', 'FETCH_HEAD'], cwd=destination)
    require(git(['rev-parse', 'HEAD'], cwd=destination).strip() == entry['commit'], 'GIT_HEAD')
    if entry['recursive']:
        git(['-c', 'protocol.file.allow=never', 'submodule', 'update', '--init',
             '--recursive', '--depth', '1'], cwd=destination, timeout=1800)
    submodules = {}
    for line in git(['submodule', 'status', '--recursive'], cwd=destination).splitlines():
        m = re.fullmatch(r' ([0-9a-f]{40}) (\S+)(?: \(.*\))?', line)
        require(m is not None, 'SUBMODULE_STATE:' + line[:80])
        submodules[m[2]] = m[1]
    return submodules


def fetch(result, cache):
    cache = Path(cache)
    cache.mkdir(mode=0o700, exist_ok=True)
    outcome = {}
    for name, entry in sorted(result['wraps'].items()):
        if entry['kind'] == 'wrap-file':
            outcome[name] = download(entry['urls'], entry['sha256'], cache / entry['filename'])
        elif entry['kind'] == 'wrap-git':
            submodules = clone(entry, cache / 'git' / entry['directory'])
            if entry['submodules'] is not None:
                require(submodules == entry['submodules'], 'SUBMODULE_COMMITS_CHANGED:' + name)
            entry['observed_submodules'] = submodules
            outcome[name] = 'CLONED'
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--fetch', type=Path, help='private packagecache directory')
    args = parser.parse_args()
    try:
        result = lock(args.source, json.loads(args.profile.read_text()))
        if args.fetch:
            result['fetch'] = fetch(result, args.fetch)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        result = {'status': 'LOCK_BLOCKED', 'reason': str(error), 'distribution': 'BLOCKED'}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'LOCK_COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
