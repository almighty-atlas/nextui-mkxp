#!/bin/sh
# SPDX-License-Identifier: MIT
# Manual NextUI Tools entry only; never stop the menu remotely.
set -eu
exec /bin/sh /mnt/SDCARD/.userdata/h700/nextui-mkxp-graphics-v1/run.sh --from-nextui-tools
