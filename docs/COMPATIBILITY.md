# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |

## H700 runtime preflight (2026-10-27)

Linux 4.9.170 is owner-reported. PR #27's Linux-4.9 sysroot and SDL-only link
are HOST evidence only: direct GLIBC_2.17 does not remove SDL's transitive
GLIBC_2.27 requirement. Installed libc definitions remain UNKNOWN/BLOCKED;
the new [host-only libc gate](H700_HOST_LIBC.md) is tested with synthetic metadata,
not the actual firmware libc. Installed SDL identity, Mali/GLES2/ION operation,
visible rendering and NextUI return remain **NOT_TESTED**. No distribution or
device-test authorization follows from the host checks.

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

## Distribution limitation (M0 / issue #3)

Binary redistribution and R36S code import are **BLOCKED** pending the
[provenance audit](SOURCES.md) and [distribution gate](DISTRIBUTION_GATE.md).
Neither R36S source availability nor its license inventory establishes a
reproducible, cleared H700 package. No engine was built or tested in this audit.

## H700 baseline limitation (issue #1)

The [owner-supplied read-only H700 inventory](H700_BASELINE.md) confirms
Linux aarch64 with an ELF64 AArch64 shell, existing framebuffer/SDL2/EGL/GLES
libraries, audio/input nodes and ~973 MiB physical memory with no swap.
**GLES context creation, graphics/audio/input functionality, loader/glibc symbol
compatibility and standalone Pak lifecycle remain NOT_TESTED.** Cloud fixture
and library/device-node presence do not establish gameplay compatibility.
