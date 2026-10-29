#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 077
fail() {
    printf 'RMXP: %s\n' "$1" >&2
    if test "${IS_NEXT-}" = yes && ! pidof nextui.elf >/dev/null 2>&1 && command -v show2.elf >/dev/null 2>&1; then
        show2.elf --mode=simple --image= --text="RMXP: $1" --fontsize=20 --texty=45 --timeout=5 || true
    fi
    exit 2
}
test "${IS_NEXT-}" = yes && test "${PLATFORM-}" = h700 || fail 'Requires NextUI H700'
pidof nextui.elf >/dev/null 2>&1 && fail 'NextUI still owns display'
test "$#" = 1 && test -f "$1" || fail 'Select a .rmxp entry'
case "$1" in *.rmxp) ;; *) fail 'Select a .rmxp entry' ;; esac
test "$(wc -c < "$1")" -le 65 || fail 'Invalid game entry'
id=$(cat "$1")
case "$id" in ''|*[!0-9a-f]*) fail 'Invalid game entry' ;; esac
test "${#id}" = 64 || fail 'Invalid game ID'
: "${USERDATA_PATH:?}" "${SDCARD_PATH:?}"
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
state="$USERDATA_PATH/nextui-mkxp/$id"
test -f "$state/source.path" && test -f "$state/mkxp.json" || fail 'Register game first'
source=$(cat "$state/source.path")
case "$source" in /*|../*|*/../*|*/..|'') fail 'Invalid source path' ;; esac
for dir in "$SDCARD_PATH/$source" "$state/game"; do
    test -f "$dir/Game.ini" || fail 'Game.ini missing'
    for asset in Data Graphics Audio; do
        test -d "$dir/$asset" || fail "$asset directory missing"
    done
done
test -x "$base/engine" && test -f "$base/SHA256SUMS" || fail 'Install private runtime first'
(cd "$base" && sha256sum -c SHA256SUMS >/dev/null 2>&1) || fail 'Runtime checksum failed'
mkdir "$state/lock" 2>/dev/null || fail 'Game busy; check lock'
engine_pid=
logger_pid=
pipe_dir=
cleanup() {
    if test -n "$engine_pid"; then kill -TERM "$engine_pid" 2>/dev/null || true; wait "$engine_pid" 2>/dev/null || true; fi
    if test -n "$logger_pid"; then kill -TERM "$logger_pid" 2>/dev/null || true; wait "$logger_pid" 2>/dev/null || true; fi
    if test -n "$pipe_dir"; then rm -f "$pipe_dir/output"; rmdir "$pipe_dir"; fi
    rmdir "$state/lock"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
mkdir -p "$state/home" "$state/data/nextui-mkxp/game"
test -f "$state/data/nextui-mkxp/game/keybindings.mkxp1" || cp "$base/keybindings.mkxp1" "$state/data/nextui-mkxp/game/"
test ! -f "$state/run.log" || mv "$state/run.log" "$state/previous.log"
pipe_dir=$(mktemp -d /tmp/rmxp-output-XXXXXX)
mkfifo "$pipe_dir/output"
# Drain output, retaining only 256 truncated lines; do not limit save-file sizes.
awk 'NR <= 256 { print substr($0,1,1024) }' < "$pipe_dir/output" > "$state/run.log" &
logger_pid=$!
cd "$state"
ulimit -c 0
env -i PATH=/usr/bin:/bin HOME="$state/home" XDG_DATA_HOME="$state/data" \
    LANG=C LC_ALL=C LD_LIBRARY_PATH="$SDCARD_PATH/.system/h700/lib" LD_BIND_NOW=1 \
    SDL_VIDEODRIVER=mali SDL_OPENGL_ES_DRIVER=1 ALSOFT_DRIVERS=alsa ALSOFT_LOGLEVEL=1 \
    ALSA_CONFIG_PATH=/usr/share/alsa/alsa.conf ALSA_PLUGIN_DIR=/usr/lib/aarch64-linux-gnu/alsa-lib \
    "$base/engine" > "$pipe_dir/output" 2>&1 &
engine_pid=$!
status=0
wait "$engine_pid" || status=$?
engine_pid=
wait "$logger_pid" || true
logger_pid=
printf 'RMXP_EXIT=%s\n' "$status" >> "$state/run.log"
test "$status" = 0 || fail 'Engine failed; see run.log'
