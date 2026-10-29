#!/bin/sh
# SPDX-License-Identifier: MIT
# Private Knight Blade boot test, manually invoked through NextUI Tools.
# Game/RTP/soundfont are owner-provided and live outside the engine stage.
set -eu
umask 077
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$base" in /tmp/nextui-mkxp-kb-boot-*) ;; *) echo INVALID_STAGING_DIRECTORY; exit 2 ;; esac
test "${1-}" = --from-nextui-tools
test "${IS_NEXT-}" = yes
test "${PLATFORM-}" = h700
command -v pidof >/dev/null
if pidof nextui.elf >/dev/null 2>&1; then
    echo REFUSE_DISPLAY_CONTENTION
    exit 2
fi
private=/mnt/SDCARD/.userdata/h700/nextui-mkxp-test
cd "$base"
sha256sum -c SHA256SUMS >/dev/null
# Owner data manifest covers shipped files only; saves added later are not listed.
(cd "$private" && sha256sum -c GAME_INPUTS.SHA256SUMS >/dev/null)
mkdir -p work "$private/data/nextui-mkxp/knight-blade"
cp keybindings.mkxp1 "$private/data/nextui-mkxp/knight-blade/keybindings.mkxp1"
work=$(mktemp -d "$base/work/run-XXXXXX")
cp mkxp.json "$work/"
mkdir "$work/home"
ulimit -c 0
cd "$work"
printf 'BOOT_LAUNCH_BEGIN\n' > run.log
set +e
env -i PATH=/usr/bin:/bin HOME="$work/home" TMPDIR="$work" \
    XDG_DATA_HOME="$private/data" LANG=C LC_ALL=C \
    LD_LIBRARY_PATH=/mnt/SDCARD/.system/h700/lib LD_BIND_NOW=1 \
    SDL_VIDEODRIVER=mali SDL_OPENGL_ES_DRIVER=1 \
    ALSOFT_DRIVERS=alsa ALSOFT_LOGLEVEL=2 \
    ALSA_CONFIG_PATH=/usr/share/alsa/alsa.conf \
    ALSA_PLUGIN_DIR=/usr/lib/aarch64-linux-gnu/alsa-lib \
    /usr/bin/timeout -k 5 1800 "$base/engine" >> run.log 2>&1 &
runner=$!
# Memory samples for later profiling; read-only /proc access.
while kill -0 "$runner" 2>/dev/null; do
    pid=$(pidof engine 2>/dev/null || true)
    if test -n "$pid"; then
        printf '%s %s\n' "$(cut -d' ' -f1 /proc/uptime)" \
            "$(grep -E '^VmRSS' "/proc/$pid/status" 2>/dev/null | tr -s ' ')" >> mem.log
    fi
    sleep 5
done
wait "$runner"
status=$?
set -e
printf 'BOOT_PROCESS_EXIT=%s\n' "$status" >> run.log
# Exit 0 only means the engine returned; title/map/gameplay need owner observation.
test "$status" = 0
printf 'BOOT_RUNNER_EXIT_OK\n' >> run.log
# Return normally; NextUI's existing launcher loop owns menu restoration.
