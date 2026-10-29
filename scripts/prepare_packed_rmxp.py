#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare an UNTESTED private RGSSAD-v1 candidate in a fresh SD-shaped tree.

No engine is copied or run. A validated archive stays intact; missing asset
mount-point directories are added only in the new source copy, and only when
the archive index provides those roots. Native mkxp-z mounts Game.rgssad itself.
"""
import argparse
import json
import os
from pathlib import Path
import shutil

import rmxp_fangame_audit as A
import rmxp_pak as P

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3


def prepare(game, expected_archive, sd, name):
    game, sd = Path(game), Path(sd).absolute()
    P.require(game.is_dir() and not game.is_symlink(), 'GAME_DIRECTORY')
    P.safe_path(name)
    P.require(name and not name.startswith('.') and not any(c in name for c in '/\\:*?"<>|'),
              'CANDIDATE_NAME')
    packed = game / 'Game.rgssad'
    P.require(packed.is_file() and not packed.is_symlink() and P.digest(packed) == expected_archive,
              'GAME_ARCHIVE_HASH')
    P.require((game / 'Game.ini').is_file(), 'GAME_INI_REQUIRED')
    for path in (game, *game.rglob('*')):
        P.safe_path(path)
        P.require(not path.is_symlink() and (path.is_dir() or path.is_file()), 'GAME_SPECIAL_FILE')
    report = A.audit(game)
    P.require(report['layout'] == 'RGSSAD_V1', 'RGSS1_REQUIRED')
    mounts = [folder for folder in ('Data', 'Graphics', 'Audio') if not (game / folder).is_dir()]
    for folder in mounts:
        P.require(folder.casefold() in report['packed_roots'], 'PACKED_MEDIA_REQUIRED')
    P.require(not sd.exists() and not sd.is_symlink() and sd.parent.is_dir(), 'FRESH_SD_STAGE_REQUIRED')
    P.require(not sd.resolve().is_relative_to(ROOT) and not sd.resolve().is_relative_to(game.resolve()),
              'PRIVATE_STAGE_REQUIRED')
    P.require(not any(p.is_symlink() for p in sd.parents), 'STAGE_SYMLINK')
    size = sum(p.stat().st_size for p in game.rglob('*') if p.is_file())
    P.require(shutil.disk_usage(sd.parent).free > 2 * size + 6 * GIB, 'FREE_SPACE_GUARD')
    sd.mkdir(mode=0o700)
    source = sd / 'Games' / name
    shutil.copytree(game, source)
    for folder in mounts:
        (source / folder).mkdir(mode=0o700)
    marker = P.register(sd, source, name, pause_menu=False)
    state = sd / '.userdata/h700/nextui-mkxp' / marker.read_text().strip()
    P.require(P.digest(source / 'Game.rgssad') == expected_archive and
              P.digest(state / 'game/Game.rgssad') == expected_archive and
              P.digest(packed) == expected_archive, 'GAME_ARCHIVE_CHANGED')
    return {'schema': 1, 'status': 'UNTESTED_CANDIDATE_PREPARED',
            'layout': 'RGSSAD_V1', 'game_archive_sha256': expected_archive,
            'game_id': state.name, 'pause_menu': 'DISABLED', 'ruby_executed': False,
            'h700_result': 'NOT_TESTED', 'script_flags': report['flags']}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--game-archive-sha256', required=True)
    parser.add_argument('--sd-stage', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.game, args.game_archive_sha256, args.sd_stage, args.name)
    except (ValueError, OSError):
        print(json.dumps({'status': 'CANDIDATE_PREPARATION_BLOCKED'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
