#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble a private allowlisted Ruby trial AFTER a fresh static ABI check.

Never connects/deploys. No stock provider is copied. Requires a previously
reviewed private ABI plan and official source already verified by the builder.
"""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import tarfile

from h700_runtime_abi import add_outputs, audit, checked, digest, require, relocatables
from h700_ruby_batch import source_check


def pure_ruby(source, destination):
    for path in sorted(source.rglob('*.rb')):
        require(not path.is_symlink(), 'SYMLINK_IN_RUBY_SOURCE')
        target = destination / path.relative_to(source)
        require(not target.exists(), 'STDLIB_COLLISION')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(0o644)


def prepare(plan, source, native, helpers, output, build_receipt, source_archive):
    require(not output.exists() and not output.is_symlink(), 'FRESH_OUTPUT_REQUIRED')
    require(output.parent.is_dir() and shutil.disk_usage(output.parent).free >= 26 * 1024**3,
            'PRIVATE_HOST_SPACE_GUARD')
    source_check(source_archive, source)
    receipt = json.loads(build_receipt.read_text())
    require(receipt['status'] == 'RUBY_EXTENSION_BATCH_BUILD_PASS', 'BUILD_NOT_PASSED')
    actual = {p.relative_to(native).as_posix(): digest(p) for p in sorted(native.rglob('*.so'))}
    require(actual == receipt['outputs'], 'BUILD_OUTPUT_HASH_CHANGED')
    add_outputs(plan, native, helpers)
    result = audit(plan)
    require(result['status'] == 'STATIC_ABI_CANDIDATES_PASS', 'STATIC_ABI_NOT_PASSED')
    require(native.name == 'aarch64-linux' and native.parent.name == '.ext', 'RUBY_OUTPUT_LAYOUT')
    result['intermediates'] = relocatables(native.parent.parent, checked(plan['readelf']))
    abi_hashes = {f['sha256'] for f in result['objects'].values()}
    require(set(actual.values()) <= abi_hashes, 'UNAUDITED_MODULE')
    extension_hashes = {f['sha256'] for f in result['objects'].values()
                        if f['role'] == 'extension' and f['soname'] is None}
    require(set(actual.values()) <= extension_hashes, 'NOT_A_RUBY_EXTENSION')
    output.mkdir(mode=0o700)
    records = {item['id']: item for item in plan['objects']}
    for name, target in [('ruby', 'ruby'), ('libruby', 'libruby.so.3.1.3')]:
        original = checked(records[name]['file'])
        shutil.copyfile(original, output / target)
        (output / target).chmod(0o755 if name == 'ruby' else 0o644)
    (output / 'libruby.so.3.1').symlink_to('libruby.so.3.1.3')
    for path in sorted(native.rglob('*.so')):
        require(not path.is_symlink(), 'SYMLINK_MODULE')
        target = output / 'native' / path.relative_to(native)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(0o644)
    stdlib = output / 'stdlib'
    pure_ruby(source / 'lib', stdlib)
    for ext in ('psych', 'fiddle', 'date'):
        pure_ruby(source / 'ext' / ext / 'lib', stdlib)
    repo = Path(__file__).resolve().parents[1]
    shutil.copyfile(repo / 'tests/hardware/ruby_runtime.rb', output / 'test.rb')
    shutil.copyfile(repo / 'scripts/h700_ruby_trial.sh', output / 'run.sh')
    for license_file in ('COPYING', 'BSDL', 'LEGAL'):
        shutil.copyfile(source / license_file, output / license_file)
    # SHA256SUMS covers every shipped file and the controlled SONAME alias.
    files = sorted(p for p in output.rglob('*') if p.is_file())
    require(all('\n' not in str(p.relative_to(output)) for p in files), 'UNSAFE_FILENAME')
    hashes = {p.relative_to(output).as_posix(): digest(p) for p in files}
    require(all(hashes['native/' + name] == h for name, h in actual.items()),
            'COPIED_ELF_CHANGED')
    (output / 'SHA256SUMS').write_text(''.join(h + '  ' + name + '\n' for name, h in hashes.items()))
    archive = output.with_suffix('.tar.gz')
    require(not archive.exists(), 'ARCHIVE_ALREADY_EXISTS')
    with archive.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as zipped:
        archive.chmod(0o600)
        with tarfile.open(fileobj=zipped, mode='w') as tar:
            for p in sorted(output.rglob('*')):
                info = tar.gettarinfo(str(p), arcname=p.relative_to(output).as_posix())
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                if info.isfile():
                    with p.open('rb') as stream:
                        tar.addfile(info, stream)
                else:
                    tar.addfile(info)
    evidence = {'schema': 1, 'status': 'PRIVATE_TRIAL_PREPARED',
                'archive_sha256': digest(archive), 'files': hashes,
                'static_abi': result, 'distribution': 'BLOCKED', 'device_execution': 'NOT_TESTED'}
    output.with_suffix('.receipt.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return {'status': evidence['status'], 'archive_sha256': evidence['archive_sha256'],
            'files': len(hashes), 'native_modules': len(actual), 'size': archive.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('plan', 'source', 'source-archive', 'native', 'helpers', 'output', 'build-receipt'):
        parser.add_argument('--' + key, required=True, type=Path)
    args = parser.parse_args()
    result = prepare(json.loads(args.plan.read_text()), args.source, args.native,
                     args.helpers, args.output, args.build_receipt, args.source_archive)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
