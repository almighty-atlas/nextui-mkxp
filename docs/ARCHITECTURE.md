# Architecture proposal (not yet validated on device)

## Target platform

- Device: Anbernic RG35XX Pro; SoC family H700.
- Firmware: official NextUI H700; **capture exact installed version**.
- Userspace: potentially aarch64/64-bit; confirm kernel, tool userland and `/bin/sh` ELF separately with [the read-only probe](DEVICE_PROBE.md). Actual H700 baseline remains **NOT_TESTED**, pending redacted owner output in issue #1.
- Key constraints: modest RAM, framebuffer/display/GLES/DRM integration, built-in buttons, filesystem permissions, SD card durability.
- R36S reference targets ArkOS on RK3326/armhf, **not a binary-compatible implementation**.

## Runtime choice / architecture decision gate

Option A (**initial preference**): standalone mkxp-z with SDL2/native GLES/audio. NextUI's documentation describes standalone Pak limitations: no default NextUI menu/quick-save/auto-resume. Graphics, input, audio and exit handling must be provided by the launcher/runtime. Verify whether NextUI's chosen graphics backend and render device can coexist with the native process.

Option B: Libretro core. **Not the baseline** because NextUI MinArch documentation states OpenGL libretro APIs are not implemented; only revisit with documented upstream change or a different frontend whose behavior is explicitly accepted.

Option C: PortMaster integration. Evaluate as packaging/source of ideas, not an assumed solution; must verify its exact H700/NextUI graphics integration before adopting.

## Component boundaries

```text
NextUI ROM entry / tool entry (discovery contract TBD)
    |
    v
RMXP.pak/launch.sh          validate selected game, environment, state
    |
    +--- per-game writable data   saves, settings, logs, clean exit
    |
    v
native aarch64 mkxp-z        SDL + GLES/DRM + audio + Ruby/RGSS
    |
    v
user-supplied game files    Game.ini, Data/, Graphics/, Audio/ ...
```

**Provisional storage** (pending M0 discovery): `Emus/h700/RMXP.pak/` for the Pak, a `Roms/... (RMXP)/` directory with launchable entries, and writable per-game state in `.userdata/h700/` using NextUI-provided environment variables. The marker/entry representation is **not finalized**: NextUI expects a ROM path argument; directory/extension filtering may need a benign file-based launcher entry. Validate against upstream Pak docs and an actual H700 unit first.

## Non-functional requirements

- Launch and exit are idempotent; no global state left modified.
- No root requirement for normal play. If any feature really requires elevation, design an opt-in, reversible, separately reviewed method.
- Keep game files outside source distribution, avoid accidental scans of sensitive content and never log secrets or full game payloads.
- Per-game stable ID for saves, config, crash logs and optional debug sampling.
- Tested behavior for interrupted write, missing assets, low memory and restart.
- No unsupported promises: `RMXP.pak` is not a universal guarantee for every RGSS script or Essentials extension.

## Open questions for M0

1. Exact H700 ABI, available linker/libc, bundled SDL/audio/GLES libraries and GPU/display backend.
2. Actual Pak runner variables and process lifecycle, ROM directory detection, paths with spaces, input/menu events.
3. Legal and reproducible reuse of R36S patches and the preferred upstream mkxp-z revision.
4. What minimum non-copyrighted smoke-test content can exercise init without distributing RGSS/game files?
