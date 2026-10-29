#!/bin/sh
# SPDX-License-Identifier: MIT
# The only Tools file for this private boot test; no binaries or game assets.
set -eu
stage=/tmp/nextui-mkxp-kb-boot-v1
if test ! -f "$stage/run.sh"; then
    echo 'Boot test payload absent (device rebooted?). Re-stage the private test.' >&2
    exit 2
fi
exec /bin/sh "$stage/run.sh" --from-nextui-tools
