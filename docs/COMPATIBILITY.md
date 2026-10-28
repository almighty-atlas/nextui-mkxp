# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## Engine input preflight (Issue #4 static preparation)

[Offline input contract and prerequisite review](H700_ENGINE_PREFLIGHT.md) records
the existing owner-confirmed **tiny02 Debian builder** (GCC 8.3 AArch64,
Linux-4.9.170/glibc-2.28, successful SDL/testbuild), not an absent build host.
That is host evidence, not clean-room reproducibility or engine compatibility.
The input manifest remains **BLOCKED** by #1/#2/#3, complete dependency/license
closure and exact current builder receipt binding. No engine/C++ cross-build,
device changes or distribution permission result from this static checker.

## C++14 calibration follow-up

[C++14 report](H700_CXX_ABI.md) binds the supplied tiny02 libstdc++/libgcc hashes,
GLIBC floors and receipt-match facts without claiming independent byte inspection.
Original probe and native runner are prepared; **HOST_BUILD_BLOCKED** here (no
native C++ compiler in PATH), **CROSS_BUILD_BLOCKED** (no local tiny02 raw receipts,
observed search paths or actual link inputs). No new ELF/map, native-runtime,
engine or H700 compatibility result. The 20-GiB floor is enforced by the runner;
tiny02 free space still needs its own measurement. Distribution remains BLOCKED.

## Ruby 3.1.3 runtime components (owner-reported H700, 2026-10-28)

| Component | H700 result | Evidence level | Limitation |
| --- | --- | --- | --- |
| Ruby 3.1.3 interpreter + core test | PASS | Owner-reported; log/firmware version not attached | Private build, not reproducible from this repo yet |
| `zlib.so` (deflate/inflate/CRC32) | PASS | Owner-reported | Private build |
| `psych.so` + bundled libyaml (load/parse/syntax error) | PASS | Owner-reported | `UTF-16LE`/`UTF-16BE` encodings missing; `safe_load`/`dump` NOT_TESTED |
| Ruby encodings (`enc/*.so`), Fiddle/libffi | NOT_TESTED | — | Not built |
| mkxp-z engine | NOT_TESTED | — | Not built; no engine start |

Details and hashes: [H700_ENGINE_PREFLIGHT.md](H700_ENGINE_PREFLIGHT.md#owner-h700-ruby-313-runtime-zlib-and-psych-trials-pass-2026-10-28).
Private artifacts are never distributed.

## Rules for updating

Always include exact game build, mkxp-z commit, NextUI version, hardware model, distribution hash if allowed, feature checklist, exit status, FPS/memory measurements and links to sanitized evidence. Test with the user's own games, **never upload or distribute game assets**. Separate upstream-reported performance from direct H700 results.
