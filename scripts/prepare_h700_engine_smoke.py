#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package a private, asset-free smoke fixture. Never deploys or runs the engine."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import tarfile

from h700_runtime_abi import digest, require

ROOT = Path(__file__).resolve().parents[1]


def prepare(prefix, output):
    prefix = prefix.resolve(strict=True)
    archive = output.with_suffix('.tar.gz')
    require(not output.exists() and not archive.exists(), 'FRESH_OUTPUT_REQUIRED')
    require(not output.resolve().is_relative_to(ROOT), 'OUTPUT_OUTSIDE_REPOSITORY_REQUIRED')
    require(shutil.disk_usage(output.parent).free >= 6 * 1024**3, 'FREE_SPACE_GUARD_6_GIB')
    evidence = json.loads((ROOT / 'build/h700-engine/engine-abi-evidence.json').read_text())
    require(evidence['status'] == 'STATIC_ABI_CANDIDATES_PASS' and
            evidence['loader_test']['status'] == 'ENGINE_LOADER_PASS', 'ABI_AND_LOADER_REQUIRED')
    engine = prefix / 'mkxp-z.aarch64'
    require(not engine.is_symlink() and digest(engine) == evidence['engine_sha256'], 'ENGINE_HASH')
    output.mkdir(mode=0o700)
    shutil.copyfile(engine, output / 'engine')
    (output / 'engine').chmod(0o700)
    fixture = ROOT / 'tests/hardware/engine-smoke'
    for name in ('smoke.rb', 'mkxp.json', 'run.sh'):
        shutil.copyfile(fixture / name, output / name)
    count = 0
    for path in sorted((prefix / 'stdlib').rglob('*.rb')):
        require(not path.is_symlink(), 'STDLIB_SYMLINK')
        target = output / 'stdlib' / path.relative_to(prefix / 'stdlib')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        count += 1
    require(count > 0, 'STDLIB_MISSING')
    shutil.copyfile(prefix / 'LICENSE.txt', output / 'LICENSE.txt')
    files = sorted(p for p in output.rglob('*') if p.is_file())
    hashes = {p.relative_to(output).as_posix(): digest(p) for p in files}
    require(all('\n' not in n and '\\' not in n for n in hashes), 'UNSAFE_FILENAME')
    require(hashes['engine'] == evidence['engine_sha256'], 'COPIED_ENGINE_CHANGED')
    (output / 'SHA256SUMS').write_text(''.join(h + '  ' + n + '\n' for n, h in hashes.items()))
    with archive.open('xb') as raw:
        archive.chmod(0o600)
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as tar:
                for path in sorted(output.rglob('*')):
                    info = tar.gettarinfo(str(path), arcname=path.relative_to(output).as_posix())
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    if info.isfile():
                        with path.open('rb') as stream:
                            tar.addfile(info, stream)
                    else:
                        tar.addfile(info)
    receipt = {'schema': 1, 'status': 'PRIVATE_SMOKE_PREPARED',
               'archive_sha256': digest(archive), 'archive_bytes': archive.stat().st_size,
               'engine_sha256': hashes['engine'], 'files': hashes, 'pure_ruby_files': count,
               'execution': 'NOT_TESTED', 'distribution': 'BLOCKED'}
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {k: receipt[k] for k in ('status', 'archive_sha256', 'archive_bytes', 'pure_ruby_files')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.engine_prefix, args.output), indent=2))


if __name__ == '__main__':
    main()
