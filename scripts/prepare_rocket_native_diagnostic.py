#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create a NEW diagnostic config; never modify a game's registration or assets."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME_ID = '6af6b0591ce6305a04030834d7a9c40a57490a98b4fb0d60e7abc4fc66273a17'
DEVICE_BASE = '/mnt/SDCARD/.userdata/h700'
STATE = DEVICE_BASE + '/nextui-mkxp/' + GAME_ID
DIAGNOSTIC = DEVICE_BASE + '/nextui-mkxp-rocket-diag-v1'
NATIVE = DEVICE_BASE + '/nextui-mkxp-graphics-v1'


def prepare(config_path, output):
    config_path, output = Path(config_path), Path(output)
    config = json.loads(config_path.read_text())
    if (config.get('rgssVersion') != 1 or config.get('gameFolder') != STATE + '/game'
            or config.get('preloadScript') != [STATE + '/compat/essentials_win32_compat.rb']
            or config.get('customScript')):
        raise ValueError('Expected the reviewed registered Rocket config')
    config['preloadScript'].append(DIAGNOSTIC + '/memory_guard.rb')
    config['rubyLoadpath'] = [NATIVE + '/stdlib', NATIVE + '/stdlib/aarch64-linux']
    config['dataPathOrg'], config['dataPathApp'] = 'nextui-mkxp-test', 'rocket-native'
    output.mkdir()  # no overwrite of any existing directory
    (output / 'mkxp.json').write_text(json.dumps(config, indent=2) + '\n')
    for name in ('run.sh', 'memory_guard.rb'):
        (output / name).write_bytes((ROOT / 'tests/hardware/rocket-native' / name).read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registered-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.registered_config, args.output)
