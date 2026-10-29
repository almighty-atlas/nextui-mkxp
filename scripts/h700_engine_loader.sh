#!/bin/sh
# SPDX-License-Identifier: MIT
# Private loader-only diagnostic: never enters mkxp-z main or initializes SDL.
set -eu
umask 077
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$base" in /tmp/nextui-mkxp-loader-*) ;; *) echo INVALID_STAGING_DIRECTORY; exit 2 ;; esac
cd "$base"
test ! -L engine
test ! -e work
printf '%s  engine\n' '33b15913859596645d4051bed403e6f0e0953e6d8366db3b06665a9a96ce73f3' | sha256sum -c - >/dev/null
mkdir -m 700 work
ulimit -f 128
loader=/lib/ld-linux-aarch64.so.1
printf 'LOADER_ONLY engine_main=NOT_EXECUTED\n'
for mode in verify list; do
    set +e
    env -i PATH=/usr/bin:/bin HOME="$base/work" LANG=C LC_ALL=C \
        LD_LIBRARY_PATH=/mnt/SDCARD/.system/h700/lib \
        /usr/bin/timeout -k 2 10 "$loader" "--$mode" "$base/engine" \
        > "work/$mode.txt" 2>&1
    status=$?
    set -e
    # Do not expose ASLR addresses in published diagnostics.
    sed 's/0x[0-9a-fA-F]*/ADDRESS/g' "work/$mode.txt"
    printf 'LOADER_%s_EXIT=%s\n' "$mode" "$status"
    test "$status" = 0
done
printf 'ENGINE_LOADER_PASS\n'
