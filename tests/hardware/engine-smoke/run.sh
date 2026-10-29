#!/bin/sh
# SPDX-License-Identifier: MIT
# Manually invoked through NextUI Tools; no killall, service or firmware changes.
set -eu
umask 077
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$base" in /tmp/nextui-mkxp-engine-smoke-*) ;; *) echo INVALID_STAGING_DIRECTORY; exit 2 ;; esac
test "${1-}" = --from-nextui-tools
test "${IS_NEXT-}" = yes
test "${PLATFORM-}" = h700
command -v pidof >/dev/null
if pidof nextui.elf >/dev/null 2>&1; then
    echo REFUSE_DISPLAY_CONTENTION
    exit 2
fi
cd "$base"
sha256sum -c SHA256SUMS >/dev/null
mkdir -p work
work=$(mktemp -d "$base/work/run-XXXXXX")
cp smoke.rb mkxp.json "$work/"
mkdir "$work/home" "$work/data"
ulimit -c 0
ulimit -f 8192
cd "$work"
printf 'SMOKE_LAUNCH_BEGIN\n' > run.log
set +e
env -i PATH=/usr/bin:/bin HOME="$work/home" TMPDIR="$work" \
    XDG_DATA_HOME="$work/data" LANG=C LC_ALL=C SRCDIR="$work" \
    LD_LIBRARY_PATH=/mnt/SDCARD/.system/h700/lib LD_BIND_NOW=1 \
    SDL_VIDEODRIVER=mali SDL_OPENGL_ES_DRIVER=1 \
    ALSOFT_DRIVERS=alsa ALSOFT_LOGLEVEL=3 \
    ALSA_CONFIG_PATH=/usr/share/alsa/alsa.conf \
    ALSA_PLUGIN_DIR=/usr/lib/aarch64-linux-gnu/alsa-lib \
    /usr/bin/timeout -k 3 45 "$base/engine" >> run.log 2>&1
status=$?
set -e
printf 'SMOKE_PROCESS_EXIT=%s\n' "$status" >> run.log
cat run.log
# mkxp-z can return 0 on initialization errors, so require our Ruby pass marker.
test "$status" = 0
grep -qx SMOKE_SCRIPT_PASS run.log
if grep -q SMOKE_FAIL run.log; then exit 1; fi
printf 'SMOKE_RUNNER_PASS\n' >> run.log
# Return normally; NextUI's existing launcher loop owns menu restoration.
