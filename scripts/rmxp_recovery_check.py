#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a separate playable snapshot recovery check, never overwrite live saves.

Python on the preparation computer, not the H700. The input is a quiescent
private state directory (or byte copy). Outputs contain private game/save data.
"""
import argparse
import json
import os
from pathlib import Path
import shutil

import rmxp_pak as P
import rmxp_state as S

ROOT = Path(__file__).resolve().parents[1]


def prepare(state, workspace, name='Knight Blade Recovery', device_root='/mnt/SDCARD'):
    state = S.validate_state(state)
    P.safe_path(name)
    P.require(name and not name.startswith('.') and not any(c in name for c in '/\\:*?"<>|'),
              'INVALID_RECOVERY_NAME')
    S.require(P.hashlib.sha256(('Games/' + name).encode()).hexdigest() != state.name,
              'RECOVERY_ID_COLLISION')
    workspace = Path(workspace).absolute()
    S.require(not workspace.exists() and not workspace.is_symlink(), 'FRESH_WORKSPACE_REQUIRED')
    S.require(workspace.parent.is_dir() and not workspace.resolve().is_relative_to(ROOT)
              and not workspace.resolve().is_relative_to(state), 'PRIVATE_OUTPUT_LOCATION')
    S.require(not any(p.is_symlink() for p in workspace.parents), 'OUTPUT_SYMLINK')
    S.require(not (state / 'lock').exists(), 'STATE_LOCKED')
    source = S.inventory(state)
    needed = 4 * sum(record['size'] for record in source['files'].values()) + 32 * 1024**2
    S.require(shutil.disk_usage(workspace.parent).free > needed, 'INSUFFICIENT_SPACE')
    workspace.mkdir(mode=0o700)
    backup = workspace / 'snapshot'
    S.snapshot(state, backup)
    restored_sd = workspace / 'restored-sd'
    restored_sd.mkdir(mode=0o700)
    S.restore(backup, restored_sd)
    restored = restored_sd / '.userdata/h700/nextui-mkxp' / state.name
    S.require(S.inventory(restored) == source, 'RESTORED_STATE_MISMATCH')

    sd = workspace / 'out-sd'
    sd.mkdir(mode=0o700)
    # A fresh source path gives registration a different stable ID. Its generated
    # config is deliberately rebased; the restored snapshot above stays bit-exact.
    game = sd / 'Games' / name
    shutil.copytree(restored / 'game', game)
    marker = P.register(sd, game, name, device_root)
    target = sd / '.userdata/h700/nextui-mkxp' / marker.read_text().strip()
    for item in ('session.conf', 'pause_menu.rb'):
        if (restored / item).is_file():
            shutil.copyfile(restored / item, target / item)
    if (target / 'pause_menu.rb').exists():
        config = json.loads((target / 'mkxp.json').read_text())
        config['preloadScript'] = [device_root + '/' + target.relative_to(sd).as_posix() + '/pause_menu.rb']
        (target / 'mkxp.json').write_text(json.dumps(config, indent=2) + '\n')
    S.require(S.inventory(state) == source, 'SOURCE_CHANGED_DURING_PREPARATION')
    S.require(S.inventory(target / 'game') == S.inventory(restored / 'game'), 'RECOVERY_GAME_MISMATCH')
    return {'status': 'RECOVERY_CHECK_PREPARED', 'restored_state': 'BIT_IDENTICAL',
            'playable_config': 'REBASED_FRESH_ID', 'hardware_load': 'NOT_TESTED'}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--name', default='Knight Blade Recovery')
    parser.add_argument('--device-root', default='/mnt/SDCARD')
    args = parser.parse_args()
    try:
        result = prepare(args.state, args.workspace, args.name, args.device_root)
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({'status': 'RECOVERY_CHECK_BLOCKED'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
