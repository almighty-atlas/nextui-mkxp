# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.

## H700 baseline limitation (issue #1)

The [owner-supplied read-only H700 inventory](H700_BASELINE.md) confirms
Linux aarch64 with an ELF64 AArch64 shell, existing framebuffer/SDL2/EGL/GLES
libraries, audio/input nodes and ~973 MiB physical memory with no swap.
**GLES context creation, graphics/audio/input functionality, loader/glibc symbol
compatibility and standalone Pak lifecycle remain NOT_TESTED.** Cloud fixture
and library/device-node presence do not establish gameplay compatibility.
