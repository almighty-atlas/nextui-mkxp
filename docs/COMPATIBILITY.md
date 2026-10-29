# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.

## Offline state maintenance candidate (#11)

[Private state tools](RMXP_STATE.md) support checked snapshots, fresh-destination
restoration and allowlisted diagnostic export for PR #40's layout. They require
Python 3.11+ on the preparation computer and a stopped game. They preserve save
bytes without interpreting RGSS data, but do not repair already-corrupt saves.
Full snapshots include private game content and must never be distributed.
Real-device recovery, physical restart/upgrade behavior and FAT32 power-loss
semantics are untested. Raw runtime logs remain private; the exported summary
does not expose their text. A shell exit code alone cannot prove crash versus
explicit high-numbered exit. See the [grouped test plan](RMXP_BATCH_TEST.md).
