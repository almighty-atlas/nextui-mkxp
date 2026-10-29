# NextUI mkxp

Native **RPG Maker XP** game runtime for **NextUI on Anbernic H700 handhelds**, initially targeting the **RG35XX Pro**. Based on [mkxp-z](https://github.com/mkxp-z/mkxp-z), with [mkxp-z-r36s](https://github.com/Periko21/mkxp-z-r36s) as an important research reference.

> **Status: Knight Blade and the private standalone Pak are verified on H700. No public binary release: licensing, corresponding source and clean-room reproducibility remain open.**

**Knight Blade progress: 100%.** Knight Blade [is playable on the RG35XX Pro](docs/KNIGHT_BLADE_BOOT.md)
(title, music, dialogue, battles, menu, save and load; owner-verified) from a private
test stage and the private RMXP.pak. See the maintained [playability roadmap](docs/KNIGHT_BLADE_ROADMAP.md).

Private Ruby 3.1.3 runtime/extension builds now have a
[verified H700 grouped test](docs/H700_RUBY_BATCH.md), including encodings,
Psych high-level API and Fiddle. This is not an mkxp-z engine start or a
publicly reproducible/releasable binary; no private artifacts are distributed.

A [private RMXP Pak integration candidate](docs/RMXP_PAK.md) now provides
game registration and a source-only installer kit. Discovery, launch, controls,
save/load, quit and reboot were tested on RG35XX Pro / NextUI-20261013-0.
The [Menu-button overlay](docs/RMXP_PAUSE_MENU.md) provides Continue/Save/Load/Quit
using the game's own save format, not emulator save states. Two-instance save
isolation and in-game loading of a restored snapshot remain explicit follow-ups.

## Goals

For the already-reviewed private runtime, use the [install/recovery guide](docs/INSTALL.md).
It is not a public binary release or a download of game/RTP files.

1. A reproducible, native **aarch64/H700** engine build compatible with the real NextUI environment.
2. An installable **RMXP.pak** with intuitive launch, input, audio, exit, save and diagnostic behavior.
3. Hardware-tested support for **Pokémon Infinite Fusion** and **Pokémon Decay**, without bundling game files.
4. Clear performance and compatibility reporting instead of unverified “supported” claims.
5. A game-agnostic design that can eventually support other RPG Maker XP titles.

## Scope and technical approach

- Target: Anbernic RG35XX Pro, H700, NextUI (record the exact firmware version in test reports).
- Start by confirming the device ABI, graphics stack and runtime libraries. **Do not copy the R36S armhf binaries:** that project targets RK3326/ArkOS and a different userspace.
- Use standalone mkxp-z as the initial candidate. [NextUI's Pak documentation](https://github.com/LoveRetro/NextUI/blob/main/PAKS.md) says MinArch does not implement OpenGL-based libretro APIs; a standalone Pak sacrifices integrated resume/quicksave.
- The R36S project is a reference, **not** evidence of performance or compatibility on H700.
- Preserve existing NextUI setup and user saves. Never assume root access or change system partitions as part of installation.

## Roadmap

| Phase | Outcome |
| --- | --- |
| M0 – Research | ABI/runtime, current NextUI Pak model, upstream licenses, hardware baseline |
| M1 – Engine | Reproducible aarch64 build and minimal on-device engine test |
| M2 – NextUI | Installable RMXP Pak, game selection, input/audio/exit/saves/logs |
| M3 – Infinite Fusion | First boot, gameplay, sprites, long-session performance |
| M4 – Decay | Essentials-specific compatibility and gameplay regression testing |
| M5 – Release | Packaging validation, instructions, CI, attribution, first release |

See [ROADMAP](docs/ROADMAP.md), [ARCHITECTURE](docs/ARCHITECTURE.md), [DEVICE-PROBE](docs/DEVICE_PROBE.md) and [TEST PLAN](docs/TEST_PLAN.md). Work is tracked in the [master roadmap issue #18](https://github.com/almighty-atlas/nextui-mkxp/issues/18) and individual [GitHub Issues](https://github.com/almighty-atlas/nextui-mkxp/issues).

[Offline state tools](docs/RMXP_STATE.md) now provide private checked snapshots,
non-overwriting recovery and privacy-safe diagnostic summaries. Results and
remaining checks are collected in one [test session](docs/RMXP_BATCH_TEST.md).
Knight Blade's private playability milestone remains **100%**; release acceptance
and other games are separate.

## Development workflow

- Take **one issue at a time** and follow the repository's [AGENTS.md](AGENTS.md).
- Implement on a short-lived branch and open a PR referencing the issue.
- Show reproducible commands, test results and any unverified hardware assumptions.
- Hardware claims need **real device evidence**; CI, emulation and R36S evidence are not substitutes.

## Distribution and licensing

**No copyrighted game files, Pokémon assets, RTP packs, proprietary fonts, save files or unofficial redistributions** in this repository, CI artifacts or release archives. Users supply their own legally obtained game files.

mkxp-z and referenced ports have their own licenses and distribution obligations. The combined binary's license, third-party inventory and corresponding-source/relinking requirements must be audited **before** distributing any binaries (see roadmap). This repository has not yet selected a license for original code.

## References

- [NextUI Paks](https://github.com/LoveRetro/NextUI/blob/main/PAKS.md)
- [Official NextUI](https://github.com/LoveRetro/NextUI)
- [mkxp-z](https://github.com/mkxp-z/mkxp-z)
- [R36S reference port](https://github.com/Periko21/mkxp-z-r36s)

_Not affiliated with Nintendo, The Pokémon Company, the RPG Maker developers or the referenced projects._
