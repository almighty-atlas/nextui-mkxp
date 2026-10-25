#!/bin/sh
# SPDX-License-Identifier: MIT
# SOURCE-ONLY template: no binary and no permission to bypass release review.
LC_ALL=C
export LC_ALL
set -f
umask 077
fail() { printf 'RMXP_VIDEO launcher_code=%s\n' "$1" >&2; exit "$1"; }
[ "$#" -eq 0 ] || fail 80
# Prevent the documented unsafe SSH-display path; this is not an attestation
# against a local user deliberately fabricating NextUI's environment.
[ -z "${SSH_CONNECTION-}${SSH_CLIENT-}${SSH_TTY-}" ] || fail 81
[ "${PLATFORM-}" = h700 ] || fail 82
[ "${DEVICE-}" = rg35xxpro ] || fail 82
[ "${SDCARD_PATH-}" = /mnt/SDCARD ] || fail 82
[ "${USERDATA_PATH-}" = /mnt/SDCARD/.userdata/h700 ] || fail 82
[ "${SYSTEM_PATH-}" = /mnt/SDCARD/.system/h700 ] || fail 82
[ "${SDL_VIDEODRIVER-}" = mali ] || fail 82
pak=$(CDPATH= cd -P "$(dirname "$0")" 2>/dev/null && pwd) || fail 83
# This committed blocker remains until an independently reviewed future package.
[ ! -e "$pak/SOURCE_ONLY" ] || fail 90
binary="$pak/bin/triangle"
[ -f "$binary" ] && [ -x "$binary" ] && [ ! -L "$binary" ] || fail 91
command -v od >/dev/null 2>&1 || fail 92
command -v awk >/dev/null 2>&1 || fail 92
# ELF64, little-endian, ET_EXEC/ET_DYN, AArch64 e_machine. Never execute for inspection.
header=$(od -An -t u1 -N 20 "$binary" 2>/dev/null) || fail 92
# shellcheck disable=SC2016 # awk byte fields, not shell expansions
printf '%s\n' "$header" | awk '
 {for(i=1;i<=NF;i++) b[++n]=$i}
 END {exit !(n==20 && b[1]==127 && b[2]==69 && b[3]==76 && b[4]==70 &&
 b[5]==2 && b[6]==1 && (b[17]==2 || b[17]==3) && b[18]==0 && b[19]==183 && b[20]==0)}' || fail 93
# Metadata preflight only; no chmod or direct opens of these nodes by the shell.
for node in /dev/fb0 /dev/ion; do
    [ -c "$node" ] && [ -r "$node" ] && [ -w "$node" ] || fail 94
done
logdir="$USERDATA_PATH/RMXP-Video-Test"
[ ! -L "$USERDATA_PATH" ] && [ ! -L "$logdir" ] || fail 95
[ ! -L "$logdir/latest.log" ] || fail 95
mkdir -p "$logdir" || fail 95
cd "$pak" || fail 83
# Per-process file-size cap (16 shell blocks; <=16 KiB on intended Linux shells).
# Never affects the parent NextUI shell. Failure refuses launch.
ulimit -c 0 || fail 96
ulimit -f 16 || fail 96
# exec preserves foreground lifetime/status and delivers own TERM/INT to C.
# No background child, daemon, timeout utility, global signal or repair script.
exec "$binary" > "$logdir/latest.log" 2>&1
