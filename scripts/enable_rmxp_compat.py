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
SHIM_SHA256 = 'e5fac2c3c1932b745fc0a6de0e0a6b78e058e513b536fc24cdc60b17b1887063'
# Earlier reviewed shims that may be replaced in place by the current one.
PREVIOUS_SHA256 = {'899a7ec157bcfa4a22010322828565c344b610e0f160e7c50d0db83905416f80',
                   '88380c8d68906764514599e02e8de82684a5c73a0821bf245afef853040b02b1',
                   '9e6faa8fbf7a31167c7a6c8317004a6e59da6bcefb9f29e3aaa095d4a0f5d0eb',
                   'bfeb0c06d9bf23458bb2a7e53a23cd88b86c47e563e47390d2903d77a2c71af5',
                   'd0245919803049ced9a4e5ebfc0bd3c153cd5f446cc6ddb534e8dc2378a9cb8b',
                   'a2295d2f6f254a603f6b36f4434ad5a0dbed21c6aa0144337518846ab70a9fa4',
                   '1b6ac0e02e5aec4a94756a1b377c850e00239949aab2d1d5275f0ceb8deb575d',
                   '18355c267e0db188682dcc4be19b4a648f198cbfb836074d54e5887820727289',
                   '5f1bba203f65ea808107722eaa12c5a67032e6c09d3356310384faedd58b311e',
                   'e3ef586e115f944c1590dc4417bf8aeba8f5751bb62f226a8a154cfaae0103c6'}
STATE_ROOT = '.userdata/h700/nextui-mkxp'
# mkxp-z options for Essentials. With the default nominal text height
# (TTF_FontHeight) the bundled Pokemon fonts render taller than reported and
# pbDrawTextPositions crops the lower half of every glyph (seen on H700).
CONFIG = {'fontHeightReporting': 1}


def write_config(config_path, config):
    config.update(CONFIG)
    temporary = config_path.with_name('mkxp.json.tmp')
    P.require(not temporary.exists(), 'Stale temporary config')
    temporary.write_text(json.dumps(config, ensure_ascii=True, indent=2) + '\n')
    os.replace(temporary, config_path)


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
        write_config(config_path, config)
        return {'status': 'COMPAT_UPGRADED', 'game_id': game_id, 'shim_sha256': SHIM_SHA256,
                'preload': preload, 'h700_result': 'NOT_TESTED'}
    P.require(config.get('preloadScript') == [], 'Existing preload; refusing to combine scripts')
    P.require(not target.parent.exists(), 'Compatibility directory already exists')
    target.parent.mkdir()
    target.write_bytes(SHIM.read_bytes())
    P.require(P.digest(target) == SHIM_SHA256, 'Shim changed while copying')
    config['preloadScript'] = preload
    write_config(config_path, config)
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
