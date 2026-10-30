#!/bin/sh
# SPDX-License-Identifier: MIT
# Uses the native diagnostic engine, never changes the normal Pak/config.
set -eu
umask 077
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
test "$base" = /mnt/sdcard/.userdata/h700/nextui-mkxp-rocket-diag-v1
test "${1-}" = --from-nextui-tools
test "${IS_NEXT-}:${PLATFORM-}" = yes:h700
! pidof nextui.elf >/dev/null 2>&1
! pidof engine >/dev/null 2>&1
native=/mnt/sdcard/.userdata/h700/nextui-mkxp-graphics-v2
state=/mnt/sdcard/.userdata/h700/nextui-mkxp/6af6b0591ce6305a04030834d7a9c40a57490a98b4fb0d60e7abc4fc66273a17
(cd "$base" && sha256sum -c SHA256SUMS >/dev/null)
(cd "$native" && sha256sum -c SHA256SUMS >/dev/null)
mkdir "$state/lock"
trap 'rmdir "$state/lock"' EXIT
mkdir -p "$base/runs"
work=$(mktemp -d "$base/runs/run-XXXXXX")
cp "$base/mkxp.json" "$work/"
mkdir "$work/home" "$work/data"
if test -f "$state/game/Game.rxdata"; then
    cp "$state/game/Game.rxdata" "$work/Game.rxdata.before-test"
    sha256sum "$state/game/Game.rxdata" > "$work/save-before.sha256"
fi
mkdir -p "$work/data/nextui-mkxp-test/rocket-native"
cp /mnt/sdcard/Emus/h700/RMXP.pak/keybindings.mkxp1 "$work/data/nextui-mkxp-test/rocket-native/"
ulimit -c 0
cd "$work"
{
status=0
env -i PATH=/usr/bin:/bin HOME="$work/home" XDG_DATA_HOME="$work/data" SRCDIR="$work" \
    LANG=C LC_ALL=C LD_LIBRARY_PATH=/mnt/SDCARD/.system/h700/lib LD_BIND_NOW=1 \
    SDL_VIDEODRIVER=mali SDL_OPENGL_ES_DRIVER=1 ALSOFT_DRIVERS=alsa ALSOFT_LOGLEVEL=1 \
    ALSA_CONFIG_PATH=/usr/share/alsa/alsa.conf ALSA_PLUGIN_DIR=/usr/lib/aarch64-linux-gnu/alsa-lib \
    NEXTUI_GL_DIAGNOSTICS=1 \
    /usr/bin/timeout -k 3 100 "$native/engine" 2>&1 || status=$?
printf '%s\n' "$status" > exit.status
} | awk 'NR <= 512 { print substr($0, 1, 1024) }' > run.log
status=$(cat exit.status)
printf 'ROCKET_DIAGNOSTIC_EXIT=%s\n' "$status" >> run.log
if test -f save-before.sha256; then
    if sha256sum -c save-before.sha256 >/dev/null 2>&1; then
        echo ROCKET_SAVE_UNCHANGED >> run.log
    else
        echo ROCKET_SAVE_CHANGED_BACKUP_PRESERVED >> run.log
    fi
fi
sync
exit "$status"
