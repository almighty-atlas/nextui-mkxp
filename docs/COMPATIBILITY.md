# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Stock-SDL video candidate preparation (Issue #22)

The owner's 2026-10-27 metadata identifies NextUI SDL2 SHA-256
`76de58c80f9a6d901fc5563711b9edc869a759c9446c5a6cd798f4c6774f7577`,
all 21 proc-triangle SDL exports, SDL GLIBC needs through 2.17 and a libc that
defines GLIBC_2.27. These are owner-reported metadata, not rendering evidence.
[Private source preparation and guarded assembly](../spikes/h700-stock-video/README.md)
retain SOURCE_ONLY. The pinned glibc-host GCC cannot start on this Alpine/musl
host (missing host ELF interpreter); a fresh AArch64 build is **BUILD_BLOCKED**.
Stock SDL's libsamplerate/vendor closure, actual relocation, Mali/GLES2/ION,
visible animation and NextUI return remain **NOT_TESTED**; distribution is BLOCKED.

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.
