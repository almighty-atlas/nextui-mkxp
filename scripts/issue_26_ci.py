#!/usr/bin/env python3
"""Offline whitespace check of the whole branch since its base merge point."""
import argparse
import subprocess


def check_whitespace(repository, base, head='HEAD'):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repository), *args], text=True,
                                       stderr=subprocess.PIPE).strip()
    base_commit = git('rev-parse', '--verify', base + '^{commit}')
    head_commit = git('rev-parse', '--verify', head + '^{commit}')
    common = git('merge-base', base_commit, head_commit)
    result = subprocess.run(['git', '-C', str(repository), 'diff', '--check', common, head_commit],
                            capture_output=True, text=True, check=False)
    return common, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', default='HEAD')
    args = parser.parse_args()
    common, result = check_whitespace('.', args.base, args.head)
    print('Checking full branch diff from ' + common)
    print(result.stdout + result.stderr, end='')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
