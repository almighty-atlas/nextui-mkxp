# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.

## RMXP Pak integration candidate

The [Issue #8 launcher](RMXP_PAK.md) is host-tested with synthetic engines only.
H700 discovery, visible errors, launch and return are untested. It requires the
private hash-pinned H700 engine and Python 3.11+ on the preparation computer.
Registration duplicates each game once; saves then stay in that private copy.
Automatic game updates, source moves, stale-lock recovery and migration are not
implemented. Exit currently relies on the game's Shutdown menu (#10 remains).
Games needing RTP/MIDI require private `Bios/RMXP` inputs. This is not a public
engine release and does not provide MinArch integration or instant resume.
