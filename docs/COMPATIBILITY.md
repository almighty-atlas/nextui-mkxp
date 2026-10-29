# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.

## Release archive tooling (#16)

The [release verifier](RELEASE.md) checks ELF headers, interpreter, GLIBC
version references, `NEEDED` and `RPATH` statically. It cannot detect `dlopen`
dependencies, missing Mali/GLES symbols or runtime behaviour on the H700.
Upgrade and rollback swap only the Pak directory. A newer engine's saves may
not load in an older one. No archive is published while the #3 gate is BLOCKED.
