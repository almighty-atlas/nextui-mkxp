#!/bin/sh
# SPDX-License-Identifier: MIT
# Only for a private hash-verified bundle under device /tmp. Never deploys a Pak.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$base" in /tmp/nextui-mkxp-runtime-*) ;; *) echo INVALID_STAGING_DIRECTORY; exit 2 ;; esac
cd "$base"
sha256sum -c SHA256SUMS > /dev/null
test ! -e work
mkdir -m 700 work
ulimit -f 128
set +e
env -i PATH=/usr/bin:/bin HOME="$base/work" TMPDIR="$base/work" LANG=C LC_ALL=C \
    RUBYLIB="$base/stdlib:$base/native" \
    /usr/bin/timeout -k 2 40 "$base/ruby" --disable=gems --disable=rubyopt \
    -EUTF-8:UTF-8 "$base/test.rb" aarch64-linux /lib/aarch64-linux-gnu/libc.so.6 \
    > work/runtime.log 2>&1
status=$?
set -e
cat work/runtime.log
printf 'RUNTIME_EXIT=%s\n' "$status"
test "$status" = 0
grep -qx RUBY_RUNTIME_BATCH_PASS work/runtime.log
