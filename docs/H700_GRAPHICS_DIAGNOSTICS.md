# Private native graphics diagnostic — #52

## Scope and provenance

Rocket repeatedly runs out of memory despite only ~25 MiB of undisposed bitmap
pixel estimates. This diagnostic is **not a fix** and contains no game/RTP data.
It must not replace `Emus/h700/RMXP.pak/engine` or its configuration.
Knight Blade remains at its independently verified 100% playability milestone.

The engine is pinned to mkxp-z commit
`37a04d14413454551a7b6aadbb4e93e67168accb`. Original engine source is GPL-2.0-or-later;
the new diagnostic header, source instrumentation tool and generated stress
script are original MIT code. The private candidate is not a public release;
existing source/reproduction/license gates still apply.

`scripts/instrument_h700_graphics.py --source-copy <separate-engine-source>`
validates all three original source hashes before writing anything, then adds
`native/graphics_diagnostics.hpp` to the copy and hooks the GL texture wrapper,
texture pool and `Bitmap::stretchBlt`. Running it on modified/wrong input fails.
Never point it at the working/shared engine source tree.

## What the counters mean

Enabled only by `NEXTUI_GL_DIAGNOSTICS=1` in the diagnostic runner:

- generated/deleted texture names; texture image definitions and redefinitions;
- estimated live/peak level-zero RGBA bytes, cumulative image and upload bytes;
- subimage uploads and attempted bitmap stretch/blit operations;
- texture-pool occupancy (a subset of live texture bytes, not additive);
- resident process pages from `/proc/self/statm` (4096-byte pages on this H700).

`NEXTUI_GL` lines are emitted at most every two seconds during relevant calls,
up to 90 reports. Texture accounting holds at most 65536 IDs and marks
`incomplete=1` if coverage is lost. Counters are shared across translation units
and called on the GL thread. No diagnostic GL calls, synchronization, GC changes
or buffer flushes are added. Only texture-wrapper calls are covered: mipmaps,
buffers, driver-internal versions, pending GPU commands and allocation failures
are not measured. Byte counts describe requested RGBA storage, not proven GPU
residency or successful driver allocation. Shader texture binds outside the
wrapper are not counted; image uploads use the wrapper's current binding.

## Reproduction and host verification

1. Make a separate private copy of the existing pinned cross-build job, preserving
   its build directory and dependencies. This is an incremental private build,
   **not** evidence of a clean-from-source public reproduction.
2. Run the instrumentation tool against that copy's `src` directory.
3. In the existing pinned sandbox, bind the copied job as `/job`, the unchanged
   GCC 8.3/sysroot/native-Ruby inputs at the original build paths, and run
   `meson compile -C /job/build -j 2`.
4. Stage only into the copied job:
   `meson install -C /job/build --no-rebuild --destdir /job/diagnostic-staged --tags mkxp-z`.
5. Assemble `engine`, its installed `stdlib`, GPL `COPYING`, and the source-only
   `tests/hardware/graphics-stress/{run.sh,stress.rb,mkxp.json}`. Hash every file
   into `SHA256SUMS` before transfer. No game files belong in this payload.

Sandbox image: `sha256:1c4ddd5655ad020d5e320e2181a04e4356af7c0e70f2be3cd5e901657cd8596b`.
Network disabled, unprivileged UID 1000, no capabilities, read-only container
root, two CPUs/4 GiB memory; pinned inputs are the existing engine build inputs
recorded in `build/h700-engine/mkxp-z-profile.json` and ABI/build evidence.

Observed 2026-10-30:

| Level | Command/check | Result |
| --- | --- | --- |
| verified-on-host | pinned-source instrumentation | PASS, all original hashes/anchors matched |
| verified-on-host | incremental AArch64 cross-build | PASS (20 build steps) |
| verified-on-host | `python3 -m unittest discover -s tests` in pinned container with Ruby | 291 tests, 290 pass, one optional skip |
| verified-on-host | new C++ ledger test | reallocation, delete, upload counts, opt-in, 64-bit sizing and unknown-ID handling pass |
| verified-on-host | synthetic Ruby stress control flow | complete run and early high-memory stop both pass; disposal in ensure verified |
| verified-on-H700 | payload hash manifest | PASS |
| verified-on-H700 | `/lib/ld-linux-aarch64.so.1 --verify ./engine` | exit 0; no engine main/rendering executed |
| verified-on-H700 | loader `--list` with existing NextUI library path | all dependencies resolved |
| verified-on-H700 | owner tool launch, generated graphics | `GRAPHICS_STRESS_COMPLETE`, `GRAPHICS_STRESS_EXIT=0`; menu process present afterward |

Installed candidate SHA-256:
`32ddd436259ba75db60abab6208f7d8556b571ed402df8ed8e3349546e3eade9`.
Payload manifest SHA-256:
`ae25e11f0f391ceec7542ae5c69f6b1161949294c653129a678cc740f1eb513e`.
Shared engine before/after SHA-256:
`33b15913859596645d4051bed403e6f0e0953e6d8366db3b06665a9a96ce73f3`.

## Manual hardware checklist (German)

1. Über NextUI **Tools → Graphics Diagnostic** starten, nicht über SSH.
2. Eine erzeugte grüne Kachelfläche ist normal. Es werden nacheinander kleine
   und sehr hohe Quellbilder sowie Bildkopien getestet (2400 Frames bei 40 FPS,
   nominell etwa eine Minute).
3. Der Test beendet sich selbst und kehrt zu NextUI zurück. Die Ruby-Seite
   beendet ihn bei mehr als 400 MiB RSS (Prüfung alle zehn Frames) oder nach
   70 Sekunden; der Runner hat zusätzlich ein 80-Sekunden-Prozesslimit.
   Das ist keine absolute OOM-Garantie: einzelne native Aufrufe können zwischen
   den Prüfungen zusätzlichen Speicher anfordern oder blockieren.
4. Kein Spiel laden, nichts speichern, keine weiteren Tasten erforderlich.
   Danach melden, ob NextUI wieder erschien oder das Gerät ausgegangen ist.
   Letzteres wäre ein Fehler, nicht ein erwartetes Testergebnis.

Payload: `.userdata/h700/nextui-mkxp-graphics-v1/`.
Logs: `runs/run-*/run.log` inside that directory. The runner checks its own
manifest, refuses a running game or menu, limits core/log output, clears the
environment and uses null audio. It does not kill NextUI, manipulate shutdown
markers, restart services or change firmware/kernel/swap settings.

`GRAPHICS_STRESS_COMPLETE` means the script completed; `GRAPHICS_STRESS_STOP`
means its memory/time cutoff was reached. Neither marker proves Rocket works.
Keep both the counters and process-exit marker when interpreting a run. A
passing generated workload does not rule out a Rocket-specific native path.

## Observed generated-workload result

The owner saw the expected green display. The script completed all three
phases; native counter reports cover more than 1.3 million attempted blits and
1,874,329,600 cumulative uploaded bytes. Resident memory ranged from 18992 to
23813 pages (about 74–93 MiB) and ended near 79 MiB. Reported live texture
level-zero estimates stayed around 5–6 MiB. No accounting overflow was reported.
The latest kernel OOM messages still refer to the earlier Rocket processes,
not this diagnostic. This workload does **not** reproduce Rocket's growth.

## Next controlled run: Rocket with native counters

`scripts/prepare_rocket_native_diagnostic.py` creates a new configuration only
from the reviewed Rocket registration. It refuses an existing output directory,
keeps the game folder, settings and compatibility preload, adds a memory guard,
and redirects diagnostic userdata to an isolated directory. The normal Rocket
entry and shared engine are untouched. Installation is hash-verified, but this
follow-up run is **not yet tested on H700**.

Manual entry: **Tools → Rocket Diagnostic**. It uses the same candidate engine
as the successful green test and reads the existing Rocket game/save. Load the
save, walk briefly (about 20 seconds), and do **not** save during this diagnostic.
No game files are packaged with the tool.

Every ten calls through `Graphics.update`, the extra preload checks resident
memory and elapsed time. Above 400 MiB or 90 seconds since preload it requests
normal exit and logs `ROCKET_DIAGNOSTIC_STOP`; the runner adds a 100-second
process timeout. These are best-effort bounds, not a guarantee against a large
allocation or stalled native operation between checks. Rendering uses normal
audio and the reviewed controller bindings. The previous Ruby stack/allocation
profiler is not enabled in this run, so native counter collection can be
compared without its sampling/inventory overhead; the experimental GC budget
and compatibility fixes otherwise remain unchanged.

On each run, the runner snapshots an existing `Game.rxdata` into the private
run directory before starting. It does not automatically save or restore it;
it reports whether its checksum changed. The normal game's lock is held for
the run and removed on exit. Log output is drained but retained only up to 512
truncated lines; **no file-size ulimit is applied to the game or its saves**.

Follow-up payload: `.userdata/h700/nextui-mkxp-rocket-diag-v1/`.
Logs and save snapshot: `runs/run-*/` below that directory. Tool payload manifest
SHA-256: `9dc959a4fd11f8eaed54bc81f4a95be8d725a3ddeadac65219000d5bbbcd1002`.
Host tests now total 293 (292 pass, one optional skip), including guard
memory/time exits, alias chaining, refusal of wrong inputs/existing outputs,
and preservation of the original registration bytes.

### First two guarded Rocket results

Both owner runs ended normally via `ROCKET_DIAGNOSTIC_STOP` rather than an OOM:
424652800 bytes at 9.75 seconds and 424595456 bytes at 8.84 seconds, both
`ROCKET_DIAGNOSTIC_EXIT=0` and `ROCKET_SAVE_UNCHANGED`. The device remained up;
the kernel log contains only the earlier OOM events. This early return is the
guard working as designed, not a claim that Rocket is fixed.

One native sample before the cutoff recorded 149863272 bytes of requested live
level-zero texture storage across 77 names. The other run hit the cutoff before
the next periodic native sample; its last sample was 12512104 bytes. Periodic
sampling therefore misses important allocation bursts around map loading.

Diagnostic engine v2 adds at most 32 `NEXTUI_GL_IMAGE` lines for image definitions
of at least 1 MiB, including dimensions, texture ID and an image-relative caller
address from `dladdr`. This captures the burst's allocation sites for offline
symbolization with the exact candidate ELF (and ELF load-address correction if
it is not PIE). The call-site wrapper is noinline; no stack walking is done.
These are still requested sizes, not a proof that driver allocation succeeded.
No memory fix, GC threshold change or higher cutoff is introduced.

V2 incremental cross-build and install staging pass; host suite remains 293
tests (292 pass, one optional skip). Device manifest and loader checks pass;
actual v2 rendering is untested. Engine SHA-256:
`e5240b938bf4b000484331e907eecce55a3921441e299de4b3a025539215165d`.
Engine payload manifest SHA-256:
`a71a214963f7b4b857ac5e21766a7c2a328eb382b6353efbd24bb8f93ef1c746`.
Updated Rocket runner manifest SHA-256:
`bbcf0b0f18531baaa2d5f912a0a672ff57f5ce8a9cd6924f0f705f1c4af095ab`.
The matching ELF is `EXEC` with first LOAD virtual address `0x400000`, not PIE.
For symbolization add `0x400000` to a resolved `caller_offset` before running
`addr2line -f -C -e <exact-v2-ELF>` (subtract one to locate the call instruction).
Function symbols are available; source line DWARF is not, so line numbers may
be reported as unknown. A zero/unresolved offset must not be symbolized as a
real caller. Tail-call optimization may attribute the return PC to a higher
caller; treat the symbol as context, not exact allocation ownership.

The guarded Rocket runner selects `nextui-mkxp-graphics-v2`; the successful
green test and original v1 engine remain separately available. Do not interpret
the v1 green test as execution verification of v2's new call-site reporting.

Rollback: while no diagnostic process is running, remove only the separately
installed `Tools/h700/Graphics Diagnostic.pak` entry and private diagnostic
directory after preserving logs. No rollback of the shared engine is needed.
