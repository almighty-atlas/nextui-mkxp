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
