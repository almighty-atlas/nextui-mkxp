#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic offline repository checks; reads only the Git index.

Findings print a rule identifier and path, never file contents.
Passing checks say nothing about H700 runtime compatibility.
"""
import argparse
import json
import os
from pathlib import PurePosixPath
import re
import subprocess
import sys

MAX_BYTES = 256 * 1024
REQUIRED = ('README.md', 'AGENTS.md', 'docs/ROADMAP.md', 'docs/ARCHITECTURE.md',
            'docs/TEST_PLAN.md', 'docs/COMPATIBILITY.md', '.gitignore')
GAME_SUFFIXES = {'.rxdata', '.rvdata', '.rvdata2', '.rgssad', '.rgss2a', '.rgss3a',
                 '.rpgproject', '.rpgmvp', '.rpgmvo', '.rpgmvm', '.sav', '.save', '.srm',
                 '.gba', '.gbc', '.gb', '.nds', '.nes', '.sfc', '.smc', '.n64', '.z64',
                 '.iso', '.cue', '.chd'}
MEDIA_SUFFIXES = {'.ogg', '.mid', '.midi', '.wav', '.mp3', '.wma', '.flac', '.m4a'}
ARCHIVE_SUFFIXES = {'.zip', '.7z', '.rar', '.tar', '.gz', '.tgz', '.xz', '.bz2', '.zst', '.exe', '.dll'}
GAME_NAMES = {'game.exe', 'game.ini', 'rgss102e.dll', 'rgss104e.dll', 'rgss202e.dll', 'rgss301.dll'}
GAME_DIRS = {'games', 'game-data', 'user-games', 'roms', 'saves', 'rtp'}
MAGIC = ((b'\x7fELF', 'ELF_BINARY'), (b'MZ', 'PE_BINARY'), (b'\xcf\xfa\xed\xfe', 'MACHO_BINARY'),
         (b'PK\x03\x04', 'ZIP_ARCHIVE'), (b'7z\xbc\xaf\x27\x1c', '7Z_ARCHIVE'),
         (b'Rar!', 'RAR_ARCHIVE'), (b'\xfd7zXZ\x00', 'XZ_ARCHIVE'), (b'\x1f\x8b', 'GZIP_ARCHIVE'),
         (b'RGSSAD', 'RGSS_ARCHIVE'), (b'\x04\x08', 'RUBY_MARSHAL'))
SECRETS = (('PRIVATE_KEY', rb'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
           ('GITHUB_TOKEN', rb'\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})'),
           ('AWS_ACCESS_KEY', rb'\bAKIA[0-9A-Z]{16}\b'),
           ('SLACK_TOKEN', rb'\bxox[abpr]-[A-Za-z0-9-]{10,}'),
           ('GENERIC_API_KEY', rb'\bsk-[A-Za-z0-9_-]{32,}'))
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')


def git(*args, data=None):
    return subprocess.run(['git', *args], input=data, capture_output=True, check=True).stdout


def index_entries():
    """Yield (mode, path, blob) from the index, including staged additions."""
    for record in git('ls-files', '-s', '-z').split(b'\0'):
        if record:
            meta, path = record.split(b'\t', 1)
            mode, blob, _ = meta.split(b' ')
            yield mode.decode(), os.fsdecode(path), blob.decode()


def read_blobs(blobs):
    request = ''.join(b + '\n' for b in blobs).encode()
    out, pos, result = git('cat-file', '--batch', data=request), 0, {}
    for blob in blobs:
        end = out.index(b'\n', pos)
        size = int(out[pos:end].split(b' ')[2])
        result[blob] = out[end + 1:end + 1 + size]
        pos = end + 2 + size
    return result


def path_rules(path):
    pure = PurePosixPath(path)
    lower = [part.lower() for part in pure.parts]
    suffix = pure.suffix.lower()
    if pure.name.lower() in GAME_NAMES:
        yield 'GAME_EXECUTABLE_OR_CONFIG'
    if suffix in GAME_SUFFIXES:
        yield 'GAME_DATA_OR_ROM'
    if suffix in MEDIA_SUFFIXES:
        yield 'GAME_MEDIA'
    if suffix in ARCHIVE_SUFFIXES or pure.name.lower().endswith(('.tar.gz', '.tar.xz')):
        yield 'ARCHIVE_OR_WINDOWS_BINARY'
    if GAME_DIRS & set(lower[:-1]):
        yield 'GAME_DIRECTORY'
    if {'graphics', 'audio'} & set(lower[:-1]) and 'tests' not in lower:
        yield 'RMXP_ASSET_DIRECTORY'
    if pure.name.lower() in ('.env', 'id_rsa', 'id_ed25519') or suffix in ('.pem', '.key', '.p12'):
        yield 'CREDENTIAL_FILE'


def content_rules(data):
    for magic, rule in MAGIC:
        if data.startswith(magic):
            yield rule
    if len(data) > MAX_BYTES:
        yield 'FILE_TOO_LARGE'
    for rule, pattern in SECRETS:
        if re.search(pattern, data):
            yield rule


def markdown_links(path, text, paths):
    directories = {str(p) for f in paths for p in PurePosixPath(f).parents}
    for target in LINK.findall(text):
        if re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I) or target.startswith('#'):
            continue
        target = target.split('#', 1)[0]
        resolved = os.path.normpath(str(PurePosixPath(path).parent / target))
        if resolved.startswith('..') or (resolved not in paths and resolved not in directories):
            yield 'BROKEN_MARKDOWN_LINK'
            return


def check():
    entries = list(index_entries())
    paths = {path for _, path, _ in entries}
    blobs = read_blobs(sorted({blob for mode, _, blob in entries if mode != '160000'}))
    findings = [('REQUIRED_FILE_MISSING', name) for name in REQUIRED if name not in paths]
    for mode, path, blob in entries:
        rules = list(path_rules(path))
        if mode == '120000':
            rules.append('SYMLINK')
        elif mode == '160000':
            rules.append('SUBMODULE')
        else:
            data = blobs[blob]
            rules += content_rules(data)
            if path.endswith('.md'):
                rules += markdown_links(path, data.decode('utf-8', 'replace'), paths)
            elif path.endswith('.json'):
                try:
                    json.loads(data)
                except ValueError:
                    rules.append('INVALID_JSON')
            elif path.endswith('.sh') or data.startswith(b'#!/bin/sh'):
                if subprocess.run(['sh', '-n'], input=data, capture_output=True).returncode:
                    rules.append('SHELL_SYNTAX')
        findings += [(rule, path) for rule in dict.fromkeys(rules)]
    return len(entries), sorted(findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='machine-readable result')
    args = parser.parse_args()
    try:
        count, findings = check()
    except (subprocess.CalledProcessError, OSError):
        print('REPO_GUARD_ERROR=GIT_INDEX_UNREADABLE', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({'schema': 1, 'files': count,
                          'findings': [{'rule': r, 'path': p} for r, p in findings]}))
    else:
        for rule, path in findings:
            print(f'FAIL {rule} {path!r}')
        print(f'REPO_GUARD={"FAIL" if findings else "PASS"} FILES={count} FINDINGS={len(findings)}')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
