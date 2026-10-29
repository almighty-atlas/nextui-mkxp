#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Enable the reviewed Essentials Win32API shim for one registered game.

Works on an SD-shaped tree (mounted card or private staging copy). Copies
rgss/essentials_win32_compat.rb into that game's own state directory and adds
it as the only preloadScript. Refuses games with any other preload (for
example the Knight Blade pause menu); an earlier reviewed shim version is
upgraded in place. The shared Pak is never modified.
"""
import argparse
import json
import os
from pathlib import Path
import re

import rmxp_pak as P

ROOT = Path(__file__).resolve().parents[1]
SHIM = ROOT / 'rgss/essentials_win32_compat.rb'
SHIM_SHA256 = '88380c8d68906764514599e02e8de82684a5c73a0821bf245afef853040b02b1'
# Earlier reviewed shims that may be replaced in place by the current one.
PREVIOUS_SHA256 = {'899a7ec157bcfa4a22010322828565c344b610e0f160e7c50d0db83905416f80'}
STATE_ROOT = '.userdata/h700/nextui-mkxp'


def enable(sd, game_id, device_root='/mnt/SDCARD'):
    sd = Path(sd).resolve(strict=True)
    P.require(re.fullmatch(r'[0-9a-f]{64}', game_id), 'Invalid game id')
    P.require(SHIM.is_file() and P.digest(SHIM) == SHIM_SHA256, 'Unverified compatibility shim')
    state = sd / STATE_ROOT / game_id
    config_path = state / 'mkxp.json'
    target = state / 'compat/essentials_win32_compat.rb'
    P.writable_destination(sd, target)
    P.require(state.is_dir() and config_path.is_file() and not config_path.is_symlink(), 'Game not registered')
    config = json.loads(config_path.read_text())
    P.require(config.get('rgssVersion') == 1, 'RGSS1 game required')
    preload = [device_root + '/' + target.relative_to(sd).as_posix()]
    if config.get('preloadScript') == preload:
        P.require(target.is_file() and not target.is_symlink() and not target.parent.is_symlink(),
                  'Installed shim missing')
        P.require(P.digest(target) in PREVIOUS_SHA256, 'Installed shim is not a known earlier version')
        replacement = target.with_name(target.name + '.tmp')
        P.require(not replacement.exists(), 'Stale temporary shim')
        replacement.write_bytes(SHIM.read_bytes())
        P.require(P.digest(replacement) == SHIM_SHA256, 'Shim changed while copying')
        os.replace(replacement, target)
        return {'status': 'COMPAT_UPGRADED', 'game_id': game_id, 'shim_sha256': SHIM_SHA256,
                'preload': preload, 'h700_result': 'NOT_TESTED'}
    P.require(config.get('preloadScript') == [], 'Existing preload; refusing to combine scripts')
    P.require(not target.parent.exists(), 'Compatibility directory already exists')
    target.parent.mkdir()
    target.write_bytes(SHIM.read_bytes())
    P.require(P.digest(target) == SHIM_SHA256, 'Shim changed while copying')
    config['preloadScript'] = preload
    temporary = config_path.with_name('mkxp.json.tmp')
    P.require(not temporary.exists(), 'Stale temporary config')
    temporary.write_text(json.dumps(config, ensure_ascii=True, indent=2) + '\n')
    os.replace(temporary, config_path)
    return {'status': 'COMPAT_ENABLED', 'game_id': game_id, 'shim_sha256': SHIM_SHA256,
            'preload': config['preloadScript'], 'h700_result': 'NOT_TESTED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sd-root', type=Path, required=True)
    parser.add_argument('--game-id', required=True)
    args = parser.parse_args()
    try:
        result = enable(args.sd_root, args.game_id)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({'status': 'COMPAT_BLOCKED', 'reason': str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
