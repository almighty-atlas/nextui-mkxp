# RG35XX Pro H700 baseline — owner-supplied evidence

**Collected:** 2026-10-25. **Evidence class:** USER-SUPPLIED H700 INVENTORY.
**Source:** read-only `tools/probe-h700.sh` at PR #20 commit
`f2e0f954b0ec3d93afa36322a7bbd0c6bb626270`, executed from the
owner's existing SSH terminal as `sh /tmp/probe-h700.sh`.
**Evidence location:** [Issue #1 owner-supplied report](https://github.com/almighty-atlas/nextui-mkxp/issues/1#issuecomment-6403001093).

This report describes observed metadata only. It does **not** establish functional
graphics, sound, input, Pak lifecycle, executable loader compatibility, mkxp-z
startup or game compatibility. The probe's printed `NOT_TESTED` is a generic
banner that predates the owner's run.

| Item | Actual probe output / confirmed reading | Limits |
| --- | --- | --- |
| Physical device | RG35XX Pro (owner-identified) | `DEVICE` hint absent in SSH, not a negative hardware finding |
| Firmware release file | `NextUI-20261013-0`, `39a06de` | Exact UI-reported release still unconfirmed |
| Base OS | `Base OS 1.4.0 (h700)` | From selected `/etc/os-release` fields |
| Kernel | `4.9.170` / `aarch64` | `uname` evidence |
| `/bin/sh` executable | ELF64, little-endian, e_machine 183 (AArch64) | Tool userland bitness and PT_INTERP not separately confirmed; `readelf` and `getconf` absent |
| Loader/libc candidate files | `/lib/ld-linux-aarch64.so.1`, `/lib/aarch64-linux-gnu/libc.so.6`, plus ARMHF variants | Presence is not version/symbol compatibility; never mix ABI libraries |
| Physical RAM | `MemTotal: 996720 kB` (~973 MiB), `MemAvailable: 878440 kB` at observation | Single sample, not maximum usable game memory |
| Swap | `SwapTotal: 0 kB`; no entries reported | No swap observed; do not enable zram/sysctl without separate review |
| Graphics | `/dev/fb0` r/w accessible; `/dev/dri/card0`, `card1` and `renderD128` absent/inaccessible | KMS/DRM cannot be assumed; framebuffer **does not** prove EGL/GLES works |
| GLES/EGL | `libEGL.so[.1]`, `libGLESv2.so[.2]` available under `/lib` | Loaded context, EGL platform/backend and actual GL driver NOT_TESTED |
| SDL2 | NextUI's `h700/lib/libSDL2-2.0.so.0.2800.5` and SDL_image/ttf present | No tested ABI or audio/video backend behavior |
| Audio | `/dev/snd/controlC0`, `/dev/snd/pcmC0D0p`, `libasound.so.2` present | Playback NOT_TESTED |
| Input | `/dev/input/event0`, `js0`, handlers incl. `js0 event1` | Controller mappings and grabbing behavior NOT_TESTED |
| NextUI directories | `/mnt/SDCARD`, `Emus/h700`, `Tools/h700`, `.system/h700`, `.userdata/h700` present | Pak launch not tested |
| Pak env vars | All listed path variables unset in the interactive SSH session | NextUI's launcher exports them later; not evidence of a Pak bug |
| Tools | `awk`, `od`, `uname` available; `getconf`, `readelf`, `file` missing | Avoid requiring GNU utilities on-device |

## Follow-up gates

1. **M0/Issue #1:** Keep actual installed UI version and standalone Pak lifecycle checks open or explicitly NOT_TESTED; save no sensitive logs.
2. **M0/Issue #2:** Inspect the pinned NextUI H700 launcher/SDL/EGL/display path in source, compare native R36S KMS/DRM and [experimental NextUI mkxpz](https://github.com/KrutzOtrem/nextui-mkxpz) (which currently lists only `tg5040`/`tg5050` in its manifest). Do not redistribute its opaque release binaries.
3. **M1/Issue #7:** Design an independent, game-free graphical context startup and clean-exit smoke test. Do not label EGL/GLES operational from library presence.
4. **M1/Issue #6:** Verify loader, libc symbol/version requirements and exact AArch64 runtime before selecting/shipping binaries.
5. **M3:** Profile the actual game's memory requirements before proposing an opt-in zram strategy.

## Verification levels

| Check | Status |
| --- | --- |
| PR #20 static syntax, ShellCheck, offline fixtures | CI PASS at `f2e0f95` |
| SSH read-only hardware inventory | OWNER-SUPPLIED H700 OBSERVATION |
| EGL/GLES context, SDL graphics, controller/audio function | NOT_TESTED |
| Pak process return/cleanup, user save isolation | NOT_TESTED |
| Engine compilation and native execution | NOT_TESTED |
| Pokémon Infinite Fusion / Pokémon Decay | NOT_TESTED |

No device software, settings, partition, kernel module or game files were changed
by this read-only probe. This is not a complete platform compatibility certification.
