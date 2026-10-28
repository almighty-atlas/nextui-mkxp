#!/bin/sh
# SPDX-License-Identifier: MIT
# The only SD-card file for this temporary test; no binaries or game assets.
set -eu
stage=/tmp/nextui-mkxp-engine-smoke-v3
if test ! -f "$stage/run.sh"; then
    echo 'Smoke payload absent (device rebooted?). Re-stage the private test.' >&2
    exit 2
fi
exec /bin/sh "$stage/run.sh" --from-nextui-tools
