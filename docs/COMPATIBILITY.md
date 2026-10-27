# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Stock-SDL video trial (Issue #22 / PR #30)

**Limited PASS, owner-observed on H700:** RG35XX Pro, NextUI, AArch64,
kernel 4.9.170. The colorful moving triangle was visible and automatically
returned after approximately five seconds to an operable NextUI menu.
[Sanitized trace, exact ELF hash and evidence boundaries](H700_VIDEO_EVIDENCE.md):
SDL 2.28.5 / `mali`, ARM Mali-G31, OpenGL ES 3.2, 297 loop frames in 5007 ms,
cleanup code 0. The exact NextUI build and explicit orientation/process audit
were not supplied. This is **not** an engine/game/performance result.

Supplied host facts: AArch64 SHA-256
`d41477f3a3803ee22e778629d4b5c9a0947cd4449e1717f1e7f347226a09a5f9`,
SDL_ONLY_HOST_LINKED, 21 SDL exports, deterministic repeat-link. No target rebuild
or independent ELF inspection was performed by this documentation agent.
HOST_VERIFIED and SOURCE_ONLY were originally present; the owner reports
SOURCE_ONLY restored after the single trial and the ELF hash checked again.
Distribution/licensing STOP remains; no further device changes are proposed.

### Earlier metadata and preparation (historical, not the latest runtime result)

The owner's 2026-10-27 metadata identifies NextUI SDL2 SHA-256
`76de58c80f9a6d901fc5563711b9edc869a759c9446c5a6cd798f4c6774f7577`,
all 21 proc-triangle SDL exports, SDL GLIBC needs through 2.17 and a libc that
defines GLIBC_2.27. These are owner-reported metadata, not rendering evidence.
[Private source preparation and guarded assembly](../spikes/h700-stock-video/README.md)
retain SOURCE_ONLY. The pinned glibc-host GCC cannot start on this Alpine/musl
host (missing host ELF interpreter); a fresh AArch64 build is **BUILD_BLOCKED**.
That was the earlier preparation host's state. The later owner trial above
demonstrates the used video path and normal return for this candidate, not an
exhaustive libsamplerate/vendor/ION or versioned-symbol inventory. Audio, engine
input, Ruby/RGSS, games, saves and stability remain **NOT_TESTED**;
distribution is BLOCKED. See the [host-only next milestone](H700_MINIMAL_ENGINE_PLAN.md).

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.
