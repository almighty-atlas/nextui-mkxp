# Compatibility matrix

**Status vocabulary:** NOT_TESTED, BLOCKED, STARTS, PARTIALLY_PLAYABLE, PLAYABLE, REGRESSION. Only mark PLAYABLE with linked on-device evidence.

| Application | Version | Runtime/Essentials | H700/NextUI result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Minimal legal test project | TBD | TBD | NOT_TESTED | — | Required before fangame tests |
| Knight Blade | Owner-supplied English build; see inventory | RMXP / RGSS1, mkxp-z 37a04d1 | PLAYABLE on RG35XX Pro / NextUI-20261013-0 | [Boot](KNIGHT_BLADE_BOOT.md), [Pak tests](RMXP_BATCH_TEST.md), [pause menu](RMXP_PAUSE_MENU.md) | Private engine; full playthrough and public release not covered |
| Pokémon Infinite Fusion | TBD (6.8.x reported on R36S only) | RPG Maker XP/mkxp-z variant TBD | NOT_TESTED | — | R36S success is not H700 evidence |
| Pokémon Decay | TBD | Confirm upstream game package / Essentials version | NOT_TESTED | — | Scripts/plugins and native dependency audit needed |
| Pokémon Sage | Owner-supplied 2.0.6.1 archive; title says 2.0 | RGSSAD v1; 209 script entries | NOT_TESTED | [Win32API shim](ESSENTIALS_WIN32_COMPAT.md) | First launch aborted before title (missing Win32API); per-game shim installed, relaunch pending; no Flash intro/GIF/online features |
| Pokémon Reborn | Owner-supplied 19.5.0 Windows | Loose loader + 193 external Ruby files | NOT_TESTED | [Host inventory](FANGAME_HOST_INVENTORY.md) | Input/config/network review pending; upstream requires 4 GB RAM+ versus H700 ~973 MiB |
| Pokémon Team Rocket Edition (LucksackGames) | Exact release unknown; supplied RAR/EXE/CAB hashed | RGSSAD v1; 211 script entries | NOT_TESTED | [Win32API shim](ESSENTIALS_WIN32_COMPAT.md) | First launch aborted before title (missing Win32API); per-game shim installed, relaunch pending; no GIF/online features |

## Current integration status (2026-10-29)

Knight Blade's first-game checklist is **100%**, with owner-confirmed image,
sound, controls, save/load, quit and NextUI return. The private Pak and Menu
overlay work on the tested firmware. Save isolation across two instances and
loading a restored snapshot in-game remain unverified. Infinite Fusion and
Decay are not tested. Licensing/source/relink and clean-room reproduction
remain release blockers. The sections below preserve each earlier trial's
scope and unknowns; their NOT_TESTED statements are historical, not a reversal
of the later hardware results.

## Historical H700 runtime preflight (2026-10-27)

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

Those authoring-host blockers describe the initial report. Tooling and SSH
were subsequently restored: the native C++14 probe and local offline tests
now pass. New Ruby batch builds ran separately with 2 CPUs / 4 GiB and a
26-GiB stop guard; historical C++ helper limits were not reused.

## Ruby 3.1.3 runtime components (owner-reported H700, 2026-10-28)

| Component | H700 result | Evidence level | Limitation |
| --- | --- | --- | --- |
| Ruby 3.1.3 interpreter + core test | PASS | Owner-reported; log/firmware version not attached | Private build, not reproducible from this repo yet |
| `zlib.so` (deflate/inflate/CRC32) | PASS | Owner-reported | Private build |
| `psych.so` + bundled libyaml (load/parse/syntax error) | PASS | Owner-reported initial trial | Unchanged bytes reused in the later high-level trial |
| Psych high-level `safe_load`/`dump`, object/alias rejection | PASS | verified-on-H700, [batch report](H700_RUBY_BATCH.md) | BaseOS 1.4.0 / NextUI-20261013-0 (39a06de); not every Psych API |
| Ruby encodings/transcoders, StringIO/Date/Set/Shellwords | PASS | verified-on-H700, [runtime log](evidence/2026-10-28-ruby-runtime.txt) | Selected roundtrips and stdlib tests only; not all 61 built encoding modules exercised |
| Fiddle + bundled libffi 3.2.1 | PASS | verified-on-H700, [batch report](H700_RUBY_BATCH.md) | Stock libc `strlen`, allocation/free; callbacks and broader FFI NOT_TESTED |
| mkxp-z cross-build / static ABI candidates | PASS | verified-on-host, [ABI report](H700_ENGINE_ABI.md) | Engine linked; exact stock provider graph and COPY sizes checked; not runtime binding |
| mkxp-z loader verify/list | PASS | verified-on-H700, [loader log](evidence/2026-10-28-engine-loader.txt) | Exact expected stock providers resolved; not an engine start or lazy-binding test |
| mkxp-z engine start, Ruby 3.1.3, GLES rendering | PASS | verified-on-H700, [smoke v2 log](evidence/2026-10-28-engine-smoke-v2.txt) | Asset-free procedural fixture only; owner saw color bars/moving square on Mali-G31 GLES 3.2; not game compatibility |
| mkxp-z audio (OpenAL Soft → ALSA) | PASS | verified-on-H700, [smoke v3 log](evidence/2026-10-28-engine-smoke-v3.txt) | Owner heard procedural SE at volume 85; a quiet v2 tone (volume 40, 200 ms) was not heard. BGM/MIDI untested; no soundfont configured |
| Knight Blade (KN_E) requirements | INVENTORIED | verified-on-host, [inventory](KNIGHT_BLADE_INVENTORY.md) | Needs Standard RTP (62 refs) and MIDI soundfont (28 tracks); 1 missing picture in game data; no Win32API; saves in working directory |
| Knight Blade (KN_E) gameplay | PLAYABLE | verified-on-H700, [boot log](evidence/2026-10-29-knight-blade-boot.txt) | Title, MIDI music, SE, new game, movement, battles, menu and saving work (owner). Save/load across fresh launches and dialogue also work. Fallback font instead of Arial; private test stage, not a Pak |
| Physical input mapping | PARTIAL | verified-on-H700, owner + log | D-pad, left stick and RGSS A/B/C/X/Y/Z/L/R work with mkxp-z defaults. Start, Select, Menu, L2/R2 unbound; Xbox-position mapping makes physical A act as Cancel. Pak needs explicit mapping and quit path |

Details and hashes: [H700_ENGINE_PREFLIGHT.md](H700_ENGINE_PREFLIGHT.md#owner-h700-ruby-313-runtime-zlib-and-psych-trials-pass-2026-10-28).
Private artifacts are never distributed.

[Current runtime pipeline/access report](H700_RUNTIME_PIPELINE.md) records
the actual authoring-container blockers, prioritized source dependency graph,
ELF gate requirements and grouped hardware checklist. No new build, static
ELF validation, test package or engine start was performed. The active task's
free-space reserve is **25 GiB**; the historical C++ helper's 20-GiB guard is
not sufficient for new work under this scope.

The preceding access report is historical: the subsequent
[Ruby extension batch](H700_RUBY_BATCH.md) implements the private build/audit/
trial slice and records new hardware PASS. It does **not** complete public
reproducibility, engine dependency closure, license review or engine startup.

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

## RMXP Pak integration candidate

The [Issue #8 launcher](RMXP_PAK.md) is host-tested with synthetic engines only.
H700 discovery, visible errors, launch and return are untested. It requires the
private hash-pinned H700 engine and Python 3.11+ on the preparation computer.
Registration duplicates each game once; saves then stay in that private copy.
Automatic game updates, source moves, stale-lock recovery and migration are not
implemented. Exit currently relies on the game's Shutdown menu (#10 remains).
Games needing RTP/MIDI require private `Bios/RMXP` inputs. This is not a public
engine release and does not provide MinArch integration or instant resume.

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

## Session supervisor candidate (#10)

[The optional native supervisor](RMXP_SESSION.md) and per-game mapping encoder
pass host tests; the supervisor cross-compiles to AArch64 with a GLIBC_2.17
requirement. Target execution, physical evdev keycodes, SDL coexistence and
Mali/audio teardown remain untested. No default event device/chord is enabled.
The controller fixture matches the prior Knight Blade mapping; that is not an
all-buttons/all-games compatibility claim. Forced termination can interrupt a
save and cannot stop kernel-uninterruptible tasks immediately. No R36S code,
game content or native binary is distributed in this candidate.

## Release archive tooling (#16)

The [release verifier](RELEASE.md) checks ELF headers, interpreter, GLIBC
version references, `NEEDED` and `RPATH` statically. It cannot detect `dlopen`
dependencies, missing Mali/GLES symbols or runtime behaviour on the H700.
Upgrade and rollback swap only the Pak directory. A newer engine's saves may
not load in an older one. No archive is published while the #3 gate is BLOCKED.

## Pause menu (#45)

The [Menu-button overlay](RMXP_PAUSE_MENU.md) works with Knight Blade on H700.
It needs standard RMXP scene classes and offers the game's own save/load
screens, not emulator save states. Customised games and Pokémon Essentials
are untested and need an adapter. Button codes were observed on
NextUI-20261013-0 and may change with firmware.
