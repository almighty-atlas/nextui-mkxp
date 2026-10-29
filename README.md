# NextUI mkxp

Native **RPG Maker XP** game runtime for **NextUI on Anbernic H700 handhelds**, initially targeting the **RG35XX Pro**. Based on [mkxp-z](https://github.com/mkxp-z/mkxp-z), with [mkxp-z-r36s](https://github.com/Periko21/mkxp-z-r36s) as an important research reference.

> **Status: planning / feasibility. One owner-observed game-free H700 video trial passed ([limited evidence](docs/H700_VIDEO_EVIDENCE.md)). No tested mkxp-z engine or installable release exists; binary distribution remains blocked.**

**Knight Blade progress: 70%.** Installed engine static ABI candidates pass; device
engine test pending. See the maintained [playability roadmap](docs/KNIGHT_BLADE_ROADMAP.md).

Private Ruby 3.1.3 runtime/extension builds now have a
[verified H700 grouped test](docs/H700_RUBY_BATCH.md), including encodings,
Psych high-level API and Fiddle. This is not an mkxp-z engine start or a
publicly reproducible/releasable binary; no private artifacts are distributed.

## Goals

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
