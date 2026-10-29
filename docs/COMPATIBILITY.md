# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.

## Session supervisor candidate (#10)

[The optional native supervisor](RMXP_SESSION.md) and per-game mapping encoder
pass host tests; the supervisor cross-compiles to AArch64 with a GLIBC_2.17
requirement. Target execution, physical evdev keycodes, SDL coexistence and
Mali/audio teardown remain untested. No default event device/chord is enabled.
The controller fixture matches the prior Knight Blade mapping; that is not an
all-buttons/all-games compatibility claim. Forced termination can interrupt a
save and cannot stop kernel-uninterruptible tasks immediately. No R36S code,
game content or native binary is distributed in this candidate.
