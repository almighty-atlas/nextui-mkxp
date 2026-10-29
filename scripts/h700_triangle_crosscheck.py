#!/usr/bin/env python3
"""Issue #24: local SDK ABI experiment only; never runs or uploads target ELF."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from h700_build_gate import archive_members, safe_extract, scan_elf, sha256


def run_build(compiler_archive, sdk_archive, source_checkout, output, lock, policy):
    out = Path(output).resolve()
    if out.exists():
        raise ValueError('output workspace must not exist')
    # Check hashes, member selection and original source before compiler execution.
    archive_members(compiler_archive, lock['compiler']['sha256'])
    selection = lock['sdk']['selected_prefixes']
    archive_members(sdk_archive, lock['sdk']['sha256'], selection)
    srcroot = Path(source_checkout).resolve()
    rev = subprocess.check_output(['git', '-C', str(srcroot), 'rev-parse', 'HEAD'], text=True).strip()
    source = srcroot / lock['triangle']['path']
    if rev != lock['triangle']['commit'] or sha256(source) != lock['triangle']['sha256']:
        raise ValueError('original PR #23 source identity mismatch')
    out.mkdir(parents=True)
    safe_extract(compiler_archive, lock['compiler']['sha256'], out/'compiler')
    safe_extract(sdk_archive, lock['sdk']['sha256'], out/'sdk', selection)
    tool = out/'compiler/x86_64-aarch64-nextui-linux-gnu'
    cc = tool/'bin/aarch64-nextui-linux-gnu-gcc'
    sysroot = tool/'aarch64-nextui-linux-gnu/libc'
    sdk = out/'sdk'
    temp = out/'tmp'; temp.mkdir()
    env = os.environ.copy()
    for name in ('CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH',
                 'GCC_EXEC_PREFIX', 'COMPILER_PATH'):
        env.pop(name, None)
    env['TMPDIR'] = str(temp)
    records = []

    def command(label, argv):
        result = subprocess.run([str(x) for x in argv], env=env, capture_output=True,
                                text=True, timeout=120)
        (out/(label+'.log')).write_text(result.stdout+result.stderr)
        records.append({'stage': label, 'argv': [str(x) for x in argv], 'exit_code': result.returncode})
        (out/(label+'.command.json')).write_text(json.dumps(records[-1], indent=2)+'\n')
        if result.returncode:
            raise ValueError(label+' failed; see isolated log')
        return result.stdout+result.stderr

    triple = command('compiler-triple', [cc, '-dumpmachine']).strip()
    if triple != 'aarch64-nextui-linux-gnu':
        raise ValueError('compiler triple mismatch')
    version = command('compiler-version', [cc, '--version']).splitlines()[0]
    if '8.3.0' not in version:
        raise ValueError('compiler version mismatch')
    object_hashes, elf_hashes = [], []
    for n in (1, 2):
        obj = out/f'triangle-{n}.o'
        elf = out/f'triangle-{n}'
        trace = command(f'compile-{n}', [cc, '--sysroot='+str(sysroot),
                        '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-I'+str(sdk/'usr/include'), '-v', '-H', '-c', source, '-o', obj])
        for header in re.findall(r'^\.+ (/[^\n]+)', trace, re.M):
            if not Path(header).resolve().is_relative_to(out):
                raise ValueError('unexpected host include: '+header)
        command(f'link-{n}', [cc, '--sysroot='+str(sysroot), obj,
                '-L'+str(sdk/'usr/lib'), '-Wl,-rpath-link,'+str(sdk/'usr/lib'),
                '-Wl,-t', '-Wl,-Map,'+str(out/f'triangle-{n}.map'), '-o', elf,
                '-lSDL2', '-lGLESv2', '-lEGL'])
        for path in re.findall(r'^LOAD (.+)$', (out/f'triangle-{n}.map').read_text(), re.M):
            if not Path(path).resolve().is_relative_to(out):
                raise ValueError('unexpected host link input: '+path)
        object_hashes.append(sha256(obj)); elf_hashes.append(sha256(elf))
    report = {'build_status': 'HOST_VERIFIED_SDK_ABI_EXPERIMENT_ONLY',
              'compiler_triple': triple, 'compiler_version': version,
              'source_sha256': sha256(source), 'commands': records,
              'object_hashes': object_hashes, 'elf_hashes': elf_hashes,
              'repeat_build_identical': elf_hashes[0] == elf_hashes[1],
              'elf_gate': scan_elf(out/'triangle-1', policy)}
    (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    if not report['repeat_build_identical']:
        raise ValueError('repeat build differs')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('compiler-archive', 'sdk-archive', 'source-checkout', 'output', 'lock', 'policy'):
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    try:
        r = run_build(a.compiler_archive, a.sdk_archive, a.source_checkout, a.output,
                      json.loads(Path(a.lock).read_text()), json.loads(Path(a.policy).read_text()))
        print(json.dumps({'build_status': r['build_status'], 'sha256': r['elf_hashes'][0],
                          'repeat_identical': r['repeat_build_identical'],
                          'h700_gate': r['elf_gate']['status']}, indent=2))
        return 2 if r['elf_gate']['status'] == 'BLOCKED' else 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'BLOCKED', 'error': str(error)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
