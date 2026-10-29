#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a private RMXP Pak and register games on a mounted SD card (Python 3.11+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ENGINE_SHA256 = '33b15913859596645d4051bed403e6f0e0953e6d8366db3b06665a9a96ce73f3'
KIT_FILES = ('pak/RMXP.pak/launch.sh', 'scripts/rmxp_pak.py', 'docs/RMXP_PAK.md')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe_path(path):
    require(not any(ord(c) < 32 or ord(c) == 127 for c in str(path)), 'Control character in path')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def writable_destination(sd, target):
    require(target.is_relative_to(sd), 'Destination outside SD card')
    for parent in (target, *target.parents):
        if parent == sd:
            break
        require(not parent.is_symlink(), 'Destination symlink')


def validate_game(path):
    require((path / 'Game.ini').is_file(), 'Game.ini missing')
    for name in ('Data', 'Graphics', 'Audio'):
        require((path / name).is_dir(), name + ' directory missing')
    for item in (path, *path.rglob('*')):
        safe_path(item)
        require(not item.is_symlink(), 'Game symlinks are unsupported')
        require(item.is_dir() or item.is_file(), 'Special file in game')


def bindings():
    # mkxp-z FORMAT_VER=3, RGSS1, SDL controller buttons (physical A = SDL B).
    buttons = [(11, 8), (12, 2), (13, 4), (14, 6), (1, 13), (0, 12),
               (6, 12), (2, 11), (3, 14), (7, 15), (8, 16), (9, 17), (10, 18)]
    records = [(2, button, 0, target) for button, target in buttons]
    records += [(3, 0, 0, 4), (3, 0, 1, 6), (3, 1, 0, 8), (3, 1, 1, 2)]
    return struct.pack('<III', 3, 1, len(records)) + b''.join(struct.pack('<IIII', *r) for r in records)


def install(sd, runtime):
    """Import only the known private runtime; never distribute it in the source kit."""
    target = sd / 'Emus/h700/RMXP.pak'
    writable_destination(sd, target)
    require(not target.exists(), 'Pak already exists; no automatic overwrite')
    require(digest(runtime / 'engine') == ENGINE_SHA256, 'Unverified engine hash')
    files = [runtime / 'engine', runtime / 'LICENSE.txt'] + sorted((runtime / 'stdlib').rglob('*.rb'))
    require(len(files) > 2, 'Ruby stdlib missing')
    for path in files:
        require(path.is_file() and not path.is_symlink(), 'Invalid runtime input')
        require(not any(p.is_symlink() for p in path.parents), 'Runtime directory symlink')
        safe_path(path)
        require('\\' not in str(path), 'Unsupported runtime filename')
    target.mkdir(parents=True)
    for path in files:
        dest = target / path.relative_to(runtime)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    shutil.copyfile(ROOT / KIT_FILES[0], target / 'launch.sh')
    (target / 'keybindings.mkxp1').write_bytes(bindings())
    (target / 'engine').chmod(0o755)
    (target / 'launch.sh').chmod(0o755)
    manifest = ''.join(f'{digest(p)}  {p.relative_to(target).as_posix()}\n'
                       for p in sorted(target.rglob('*')) if p.is_file())
    (target / 'SHA256SUMS').write_text(manifest)
    return target


def register(sd, game, name, device_root='/mnt/SDCARD'):
    sd = sd.resolve(strict=True)
    safe_path(game)
    require(not any(p.is_symlink() for p in (game, *game.parents)), 'Game directory symlink')
    game = game.resolve(strict=True)
    require(game.is_relative_to(sd), 'Game must be on this SD card')
    relative = game.relative_to(sd).as_posix()
    require(relative not in ('.', '') and relative.split('/')[0] not in ('.userdata', '.system', 'Emus'),
            'Use a dedicated game directory, e.g. Games/Knight Blade')
    safe_path(name)
    require(name and not name.startswith('.') and not any(c in name for c in '/\\:*?"<>|'), 'Invalid entry name')
    validate_game(game)
    game_id = hashlib.sha256(relative.encode('utf-8')).hexdigest()
    state = sd / '.userdata/h700/nextui-mkxp' / game_id
    marker = sd / 'Roms/RPG Maker XP (RMXP)' / (name + '.rmxp')
    writable_destination(sd, state)
    writable_destination(sd, marker)
    # NextUI uses 256-byte buffers, including shell-escaped command arguments.
    def escaped(s):
        return s.replace("'", "'\\''")
    device_marker = device_root + '/' + marker.relative_to(sd).as_posix()
    command = "'" + escaped(device_root + '/Emus/h700/RMXP.pak/launch.sh') + "' '" + escaped(device_marker) + "'"
    require(len(command.encode('utf-8')) < 256, 'NextUI command exceeds 255 bytes')
    require(not state.exists() and not marker.exists(), 'Already registered; preserve existing saves')
    size = sum(p.stat().st_size for p in game.rglob('*') if p.is_file())
    require(shutil.disk_usage(sd).free > size + 32 * 1024**2, 'Not enough space for private game copy')
    state.mkdir(parents=True)
    # A failed copy leaves an unregistered state, never an entry pointing at partial data.
    shutil.copytree(game, state / 'game')
    device_state = device_root + '/' + state.relative_to(sd).as_posix()
    pak = device_root + '/Emus/h700/RMXP.pak'
    config = dict(rgssVersion=1, gameFolder=device_state + '/game',
                  RTP=[device_root + '/Bios/RMXP/Standard'],
                  midiSoundFont=device_root + '/Bios/RMXP/TimGM6mb.sf2',
                  rubyLoadpath=[pak + '/stdlib', pak + '/stdlib/aarch64-linux'],
                  dataPathOrg='nextui-mkxp', dataPathApp='game',
                  fullscreen=True, fixedAspectRatio=True, defScreenW=640, defScreenH=480,
                  winResizable=False, smoothScaling=0, vsync=False, enableBlitting=False,
                  enableSettings=False, enableReset=False, JITEnable=False, YJITEnable=False,
                  midiChorus=False, midiReverb=False, pathCache=True, allowSymlinks=False,
                  preloadScript=[], patches=[])
    (state / 'mkxp.json').write_text(json.dumps(config, ensure_ascii=True, indent=2) + '\n')
    (state / 'source.path').write_text(relative + '\n', encoding='utf-8')
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(game_id + '\n')
    return marker


def validate_archive(path):
    with zipfile.ZipFile(path) as archive:
        require(sorted(archive.namelist()) == sorted(KIT_FILES), 'Unexpected or duplicate archive entry')
        for info in archive.infolist():
            require(info.file_size < 128 * 1024, 'Oversized source file')
            require((info.external_attr >> 16) & 0o170000 != 0o120000, 'Archive symlink')
        require(archive.testzip() is None, 'Corrupt archive')


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('install')
    p.add_argument('--sd-root', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    p = sub.add_parser('register')
    p.add_argument('--sd-root', type=Path, required=True)
    p.add_argument('--game', type=Path, required=True)
    p.add_argument('--name', required=True)
    p = sub.add_parser('kit')
    p.add_argument('archive', type=Path)
    p = sub.add_parser('validate')
    p.add_argument('archive', type=Path)
    args = parser.parse_args()
    if args.action == 'install':
        print(install(args.sd_root.resolve(strict=True), args.runtime.resolve(strict=True)))
    elif args.action == 'register':
        print(register(args.sd_root, args.game, args.name))
    elif args.action == 'kit':
        with zipfile.ZipFile(args.archive, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in KIT_FILES:
                archive.write(ROOT / name, name)
        validate_archive(args.archive)
    else:
        validate_archive(args.archive)


if __name__ == '__main__':
    main()
