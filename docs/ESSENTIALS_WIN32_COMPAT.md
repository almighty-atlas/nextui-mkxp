# Essentials Win32API compatibility shim (#52)

## Observed failure (verified-on-H700)

First owner launch of Pokemon Sage and Pokemon Team Rocket on 2026-10-29
(NextUI-20261013-0, engine `33b15913…`). Both stopped before the title screen
with the same error in their `run.log`:

```
004:Win32API:3:in `initialize': wrong number of arguments (given 4, expected 0) (ArgumentError)
```

The H700 engine is built with `use_miniffi: false`
([profile](../build/h700-engine/mkxp-z-profile.json)), so no `Win32API`
class exists. Essentials 17.2's script 4 reopens `Win32API` and creates
handles in its class body. Simply enabling MiniFFI would not help: the games
load `user32`/`kernel32` and similar Windows libraries, which do not exist on Linux.

## Adapter

[`rgss/essentials_win32_compat.rb`](../rgss/essentials_win32_compat.rb) (MIT,
original) is enabled **per game** as its only `preloadScript`. It:

- defines `Win32API.new(dll, function, ...)`. Every call answers like an
  unavailable API: 0, `ERROR_FILE_NOT_FOUND` for the registry, `E_FAIL` for
  shell folders, an MCI error. Loading native code is never attempted;
- reports a consistent window/thread identity, so `pbFindRgssWindow` and
  `pbSameThread` succeed, and fills window rectangles with the game resolution;
- answers `GetAsyncKeyState` from the engine's **own** RGSS button state.
  Essentials replaces `Input` with Windows key polling, so this keeps the
  reviewed gamepad bindings. Exactly one virtual key per button
  (Enter=C, Esc=B, Z=A, PageUp/PageDown=L/R, F5=F5 or RGSS X), because
  Essentials polls its key aliases lazily. Several "pressed" aliases would
  re-trigger one press on later frames (found by the private harness below);
- turns `FontInstaller.install` into a no-op once the game defines it.
  mkxp-z registers the game's `Fonts/` itself, and the Windows font-folder
  copy could only fail with a prompt on every start.

Consequences visible to the player: no Flash intro in Sage (skipped as "not
playing"), no GIF conversion, no screenshot DLL, no CD/MCI/wave recording, no
online/socket features. Saves resolve to `./Game.rxdata` in the game's private
copy, because the known-folder lookup fails.

## Ruby 1.8 syntax repair

Second owner launch (verified-on-H700): the shim loaded, but both games then
stopped on parse errors. RGSS1 is Ruby 1.8, and the engine runs Ruby 3.1:

| Game | Section:line | Construct |
| --- | --- | --- |
| Sage | 046 AudioUtilities:919 | `when 0:` (colon instead of `then`) |
| Sage | 171 PSystem_Utilities:199, Rocket 190:300 | `\x7f-\x9f` in a regexp (invalid in UTF-8) |
| Sage | 184 SAGE Battle MoveEffects:401 | `x=0.` before `elsif`/`end` |

mkxp-z decodes `$RGSS_SCRIPTS` before running preloads, so the shim rewrites
the decoded text of a section **in memory** before it is evaluated. Game files
are never changed. Three narrow rules exist, one for each construct above. They
keep line numbers, skip sections with invalid UTF-8, and a rewritten section is
kept only if it then compiles. Private host harness: all 209 Sage and 211
Rocket sections compile after the repair. Only the lines listed above change.

## Runtime environment and Ruby 1.8 core methods

Third owner launch (verified-on-H700): all sections parsed and the intro
started, then both games stopped in `Dir.chdir(ENV["TEMP"])`. Windows always
sets `TEMP`, but the launcher starts the engine with an empty environment.
The shim now defaults `TEMP`/`TMP` to the launcher's per-game `HOME`.

It also restores the Ruby 1.8 core methods these games call, unless a game
defines them itself: `Array#nitems` (party and box counts), `Hash#index`,
`Object#id`/`#type` and `TRUE`/`FALSE`/`NIL`. This is an original
implementation of the idea in mkxp-z's CC0 `ruby_classic_wrap.rb`.
Fourth launch (owner, verified-on-H700): Sage reached its title screen, then
stopped in `Thread.critical` (a 1.8 scheduler lock, now a plain flag) and in
the archive reader. Essentials' `StringInput` indexes its string, which gave
bytes in 1.8; a prepended module now runs the game's own methods on a binary
copy, returns Integer bytes from `getc` and returns text in the original
encoding.

Fifth launch (owner, verified-on-H700): both games reach new game and name
entry. They then stopped because Ruby 3's `Marshal.load` reads IO-like objects
via `getbyte`, which `StringInput` now provides. Both games also sat in the
top-left 512x384 of a 640x480 screen, because Essentials resizes the Windows
window through Win32API. The shim now resizes the native screen once per frame
to the game's `Graphics.width`/`height` plus any border offsets, and mkxp-z
scales that to the display. Open items: Sage quits without an error when Down
is pressed on the load menu, and name-entry letters are cut in half. For the
quit, the shim logs `NEXTUI_EXIT`/`NEXTUI_SCENE_NIL` with callers in `run.log`.

The first version of that screen hook prepended a module to `Graphics`.
Because the games `alias` `Graphics.update` themselves, the alias captured the
prepended method, which then recursed until the stack overflowed and both games
stopped at start (sixth launch, verified-on-H700). `Graphics.update` and
`Kernel#exit` are now chained with `alias`, like the games do, and the
synthetic suite chains them the same way as a regression test.

Seventh launch (owner, verified-on-H700): both games start and fill the
screen. The load menu works, and Sage continues past name entry. A read-only
framebuffer capture of Rocket's name entry showed only the upper half of
every glyph. `pbDrawTextPositions` draws each string into a rectangle exactly
`text_size.height` tall. mkxp-z's default nominal height (`TTF_FontHeight`) is
smaller than what the bundled Pokemon fonts render, so the lower half is
cropped. `enable_rmxp_compat.py` therefore also sets `"fontHeightReporting": 1`
(rendered height) in the game's own `mkxp.json`.

Eighth launch (owner, Rocket, verified-on-H700): name-entry text was complete,
the game continued and saved, then stopped when the player talked to a
character. Essentials registers handlers such as
`Events.onAction += proc { return if ... }`. In Ruby 1.8 `proc` created a
lambda, so `return` just left the handler. In Ruby 3 it raises
`LocalJumpError`, because the section that defined the proc has finished.
`Proc#call` now ends only the called proc with the jump's value, as a 1.8
lambda did.

Ninth launch (owner, Rocket, verified-on-H700): talking to characters works.
The owner saw occasional frame drops while walking. A read-only `/proc`
sample showed the Ruby (`rgss`) thread at about 67% of one core, while the GPU
driver and audio threads were negligible. For a targeted diagnosis, the shim
has an opt-in profiler. It is active only while `$HOME/nextui-profile`
exists in the game's per-game home. Every 10 s it appends frame counts, frames
over 50 ms, GC time and the most frequently sampled game code locations to
`$HOME/nextui-profile.log`.

Tenth launch (owner, Rocket, verified-on-H700): after a long session with
several saves, the kernel OOM-killed the engine (exit 137): anon-rss 236 MB,
file-rss 640 MB of mostly GPU mappings. Essentials leaves many bitmaps to the
garbage collector instead of disposing them. Ruby only sees the small wrapper
objects and rarely collects, while the textures fill memory. The shim counts
the pixel bytes of created bitmaps that have not been disposed, and runs
`GC.start` every 48 MiB. The profiler line now also reports RSS and these
collections. The save from that session was intact.

Two agent-initiated SSH launches (stopping `nextui.elf` and queueing the game
through `/tmp/next`) were each followed by a full power-off of the device; the
owner's normal menu launch was not. Agent remote launches are stopped until
that is understood.

Known remaining 1.8 difference: `String#[]` returns a character, not a byte,
so byte checks such as GIF/BOM detection quietly evaluate to false.

`scripts/enable_rmxp_compat.py` copies the hash-pinned shim into
`.userdata/h700/nextui-mkxp/<id>/compat/` and sets the preload. An earlier
reviewed shim version is upgraded in place. It refuses other
existing preloads (e.g. the Knight Blade pause menu) and never touches the
shared Pak. Knight Blade is unaffected.

## Memory/performance follow-up — 2026-10-30

**verified-on-H700, Rocket, NextUI-20261013-0:** the owner repeated normal
play after the bitmap-budget change. Severe stutter persisted and the kernel
again killed the engine: `RMXP_EXIT=137`, `SIGNAL=9`. Kernel accounting at the
kill was anon-rss 154316 kB and file-rss 725080 kB. This is not a Ruby exception.

The four available 10-second profiler windows reported:

| Frames | Frames over 50 ms | Longest interval (ms) | GC time (ms) | RSS (MiB) | Budget-triggered collections |
| --- | --- | --- | --- | --- | --- |
| 222 | 7 | 3125 | 841 | 172 | 0 |
| 349 | 6 | 819 | 290 | 388 | 0 |
| 344 | 13 | 254 | 129 | 519 | 0 |
| 362 | 8 | 247 | 145 | 528 | 0 |

Startup/loading may be included in these intervals. Sampling often sees
`Graphics.update` (which also waits for rendering/frame pacing); that alone
does not identify CPU work. Other frequent locations are file existence checks
and archive reads. The earlier claim that these samples established a Ruby CPU
bottleneck was too strong. GPU/file mappings are also not exclusively textures.

The bitmap-budget workaround **did not prevent the OOM**. Its counter subtracts
disposals and estimates only one `width * height * 4` image per construction;
it is neither live native memory nor cumulative allocation pressure. Native
animated GIF loading allocates one texture per frame, and native clones and
other temporary allocations are not all observed by `Bitmap#initialize`.
These are confirmed accounting gaps, not proof of the actual leak's cause.
The upstream texture reuse pool is bounded to 20 MB by default.

Next step: measure bitmap creation/disposal/clone counts, animated-frame bytes,
and native texture allocations/releases alongside RSS, before choosing a memory
fix. Keep profiling bounded and compare identical gameplay with profiling off
to quantify its overhead. Do not lower a GC threshold, enable swap/zram, change
kernel settings, or claim stability based on the existing synthetic tests.
No runtime change was deployed for that initial evidence report.

### Allocation telemetry v2 (host-tested; device installation verified)

The subsequent diagnostic shim counts creations, `initialize_copy` (clone/dup)
and actual base `Bitmap#dispose` calls separately, with cumulative estimated
pixel bytes for each category. Estimates include `frame_count` for native
animations. Every report also inventories uncollected Bitmap wrappers, disposed
wrappers and estimated pixels in currently undisposed objects. No bitmap is
retained by the telemetry and no finalizer is added. Allocation-site and size
tables are bounded to 32 keys plus an overflow bucket; only the top four are
logged. Native temporary textures and driver residency still require engine-side
instrumentation; these Ruby counters must not be labelled actual GPU usage.

The profiler separately times the captured native `Graphics.update` (including
rendering/waiting), reports its own reporting overhead, samples stacks at 20 Hz
rather than 100 Hz, and stops at a 256 KiB existing-log threshold (the final
report can overshoot the threshold by one bounded report). The GC budget and
game logic are unchanged. With the profiling flag absent, no bitmap inventory
or additional clock measurements are made.

Installed for Sage and Rocket without starting either game; installed SHA-256
`e5fac2c3c1932b745fc0a6de0e0a6b78e058e513b536fc24cdc60b17b1887063`.
Existing saves matched their pre-install hashes. Old shim and profile log were
retained as `compat/essentials_win32_compat.rb.before-telemetry` and
`home/nextui-profile.before-telemetry.log` (if that log existed).

Next hardware observation: load Rocket normally, walk for **20–30 seconds**,
then quit normally; do not deliberately run to another OOM. Collect the new
profile and compare RSS against create/copy/dispose and live-pixel estimates.
The telemetry is not a memory fix and does not establish stability.

## Verification

| Level | Check | Result |
| --- | --- | --- |
| verified-on-host | Synthetic Ruby suite `tests/essentials_win32_compat_test.rb` (Ruby 3.1.3, pinned container) | allocation, animation/copy/disposal accounting, opt-in/report-size limits covered; root suite 288 tests, 287 pass, one optional skip |
| verified-on-host | Private harness (not committed) that loads both games' real Win32API, controls, file and font-installer scripts after the shim | Window found; trigger only on first held frame; repeat from frame 21; release, dir4/dir8, B, A, F5 OK; save folder `.`; registry default; font installer no-op |
| verified-on-host | Synthetic Ruby 1.8 repair cases in the same suite | PASS |
| verified-on-H700 | Shim + updated `mkxp.json` installed for both games, prior `mkxp.json` kept as `mkxp.json.pre-compat` | checksums PASS; existing saves and shared runtime unchanged |
| verified-on-H700 | Second launch with first shim | Win32API error gone; Ruby 1.8 parse errors above |
| verified-on-H700 | Repaired shim `88380c8d…` upgraded in place for both games | checksums PASS; saves and shared runtime unchanged |
| verified-on-H700 | Third launch | all sections parsed; intro reached; `ENV["TEMP"]` nil abort |
| verified-on-H700 | Shim `9e6faa8f…` (TEMP, Ruby 1.8 core methods) upgraded in place | checksums PASS; saves and shared runtime unchanged |
| verified-on-H700 | Fourth launch (Sage, owner) | title screen reached; `StringInput` byte error |
| verified-on-host | Private harness: both games' real `StringInput` + `FileInputMixin` after the shim | words/dwords/bytes and UTF-8 lines read correctly |
| verified-on-H700 (owner) | Title/menu, new game, name entry, Rocket dialogue and saving | exercised; see chronological observations above |
| failed-on-H700 | Sustained Rocket play with bitmap budget | OOM repeats; severe stutter persists |
| untested | Sustained stability, battle coverage and performance acceptance | not established |

Rollback per game: restore `mkxp.json.pre-compat` over `mkxp.json`, then remove
`compat/`.
