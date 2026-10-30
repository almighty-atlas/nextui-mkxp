#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 077
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
test "$base" = /mnt/sdcard/.userdata/h700/nextui-mkxp-graphics-v1
test "${1-}" = --from-nextui-tools
test "${IS_NEXT-}:${PLATFORM-}" = yes:h700
! pidof nextui.elf >/dev/null 2>&1
! pidof engine >/dev/null 2>&1
cd "$base"
sha256sum -c SHA256SUMS >/dev/null
mkdir -p runs
work=$(mktemp -d "$base/runs/run-XXXXXX")
cp stress.rb mkxp.json "$work/"
mkdir "$work/home" "$work/data"
ulimit -c 0
ulimit -f 2048
cd "$work"
status=0
env -i PATH=/usr/bin:/bin HOME="$work/home" XDG_DATA_HOME="$work/data" SRCDIR="$work" \
    LANG=C LC_ALL=C LD_LIBRARY_PATH=/mnt/SDCARD/.system/h700/lib LD_BIND_NOW=1 \
    SDL_VIDEODRIVER=mali SDL_OPENGL_ES_DRIVER=1 ALSOFT_DRIVERS=null \
    NEXTUI_GL_DIAGNOSTICS=1 \
    /usr/bin/timeout -k 3 80 "$base/engine" > run.log 2>&1 || status=$?
printf 'GRAPHICS_STRESS_EXIT=%s\n' "$status" >> run.log
sync
exit "$status"
