# Issue #22: source-only H700 video feasibility spike

**SOURCE_ONLY_BLOCKED — no installable package or H700 executable is supplied.**
Refs [issue #22](https://github.com/almighty-atlas/nextui-mkxp/issues/22). The owner
accepted the limited spike in [PR #21's review](https://github.com/almighty-atlas/nextui-mkxp/pull/21#issuecomment-6403356665),
not an engine build, binary release or hardware PASS. No device was accessed.

This leaf directory adds original C/shaders, a guarded launcher template, explicit
MIT terms **for these original files only**, a provenance snapshot and offline
mock tests. It changes none of the files in unmerged PRs #19/#20/#21. It does not
implement or start issues #4/#5/#6/#7 or run mkxp-z or games.

## First concrete blocker and current action

The installed SDL build identity, exact loader/libc requirements and linked-library
rights are not verified. NextUI's toolchain recipe uses an external image/SDK;
there is no verified digest/sysroot manifest for this device. The cloud has `cc`
and `readelf` but no H700 cross compiler, SDL2/GLES2/EGL development headers,
BusyBox or ShellCheck. No toolchain image/SDK, vendor binary or package was fetched,
no target binary was created, and no release/archive was uploaded.

The allowed fallback in the issue is therefore used: **review original source,
mock behavior and the build/rights plan first**. Do not copy the source template
onto the handheld, remove `SOURCE_ONLY`, or try to launch it. There is currently
**no owner hardware command to run**. The conditional manual plan below applies
only to a future independently reviewed compatible package.

## Source-confirmed intended runtime

The [immutable provenance snapshot](provenance.json) records commits, URLs and
locally computed SHA-256 for the relevant source files, not dependency approval.

- NextUI `5291344b3aceae5fa197437a70824afb41e2d338`:
  [H700 init lines 24–47](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/bin/h700-init.sh#L24-L47)
  selects `SDL_VIDEODRIVER=mali` and EGL/GLES candidates;
  [launcher lines 10–38](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/MinUI.pak/launch.sh#L10-L38)
  sets paths/library search order;
  [lines 136–166](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/MinUI.pak/launch.sh#L136-L166)
  waits for queued Tools commands after UI exit and restarts the UI afterward.
  **Never source/replay this firmware script.**
- H700 toolchain `04faa348c112617fc6b99be62308099ee6d43581`:
  [build-sdl2.sh](https://github.com/LoveRetro/h700-toolchain/blob/04faa348c112617fc6b99be62308099ee6d43581/support/build-sdl2.sh#L11-L64)
  pins SDL fork `d4a7d7503524cc469fe775242f3f925d4dd56c88`, applies its joystick patch,
  enables Mali/GLES/shared SDL and disables KMSDRM/X11/Wayland. This research recipe
  is not proof of the installed `.2800.5` library's source or ABI.
- That SDL fork's [video init](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_malivideo.c#L135-L175)
  requires `/dev/fb0` **and `/dev/ion`**. Default blitter/window creation uses ION,
  vendor pixmap entrypoints and EGL surfaces
  [lines 436–477](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_malivideo.c#L436-L477).
  Ordinary SDL KMSDRM builds do not provide this route. No blitter/rotation override
  or automatic software fallback is attempted.
- The [ADR in PR #21](https://github.com/almighty-atlas/nextui-mkxp/blob/94c2e0287df8776680d89bc33c184db4dc61935f/docs/ADR-0001-h700-native-pak.md)
  remains a proposal. The owner's [sanitized H700 metadata](https://github.com/almighty-atlas/nextui-mkxp/issues/1#issuecomment-6403001093)
  establish Base OS 1.4.0 / NextUI-20261013-0, kernel 4.9.170, an AArch64 shell,
  library/node presence and no swap; not working EGL, ION or clean display return.

## Program, failure stages and timing

`triangle.c` initializes **only SDL video + timer**, rejects SSH environment hints,
requires inherited `mali` and the actual Mali backend, sets ES2 attributes before
creating one 640×480 OpenGL window/context and making it current. It logs compiled/
linked SDL versions, bounded single-line GL/EGL vendor/renderer/version values,
compiles original in-memory shaders, uploads colored vertices and animates a
triangle through uniforms, `glDrawArrays` and real SDL buffer swaps. It validates
an ES2-or-later identity; an unknown/software renderer still cannot establish PASS.

| Code | First failed stage / meaning |
| --- | --- |
| 0 | C draw loop completed; **owner observation and clean UI return still required** |
| 10–14 | Signal setup, missing `mali` hint, SDL init/backend, GL attributes |
| 15–19 | Window, context, make-current, current EGL display or GLES identity |
| 20–24 | Shader compile, program link, uniform, buffer or drawable setup |
| 25 / 27 | GL draw error / SDL swap error (error text is not logged) |
| 26 | Clock/frame bound reached without a complete timed animated run |
| 30 / 31 | SDL_QUIT/own TERM/INT interruption / SSH launch refused |
| Launcher 80–83 | Arguments, SSH, invalid H700/device/path/backend context or Pak path |
| Launcher 90–93 | SOURCE_ONLY guard, missing executable, missing inspection tools or wrong ELF ABI |
| Launcher 94–96 | Missing fb0/ION access, unsafe/unwritable owned log location or unavailable process resource limits |

The animation loop checks a wrap-safe SDL tick deadline before each draw and ends
at 5000 ms, with an independent 625-frame cap if the clock stops. One event per
iteration prevents an event flood starving the deadline. Own TERM/INT handlers set
only a signal-safe flag; cleanup deletes GL objects/context/window and quits SDL,
including partial-init failure. No explicit joystick/gamecontroller or audio initialization, direct raw input
stream access, game file, daemon or global process signaling is used. SDL video
may itself initialize event handling; this is not a read-only metadata probe.

**Timing limit:** these bounds constrain application scheduling, not a hard
wall-clock guarantee against a blocked SDL/EGL/driver call (including init, swap
or cleanup). No watchdog is implemented: driver/kernel hangs cannot be safely
repaired here. A stalled call may prevent five-second return despite the deadline.
That remains a hardware risk for review; stop on failure. Do not claim a guaranteed
timeout or add a global timeout/kill/reboot workaround.

The foreground launcher uses `exec` and returns the application's status to
NextUI. It checks the first 20 ELF bytes for ELF64/little-endian/AArch64/ET_EXEC
or ET_DYN **without executing the file for inspection**. This is a coarse ABI
screen, not validation of PT_INTERP, GLIBC versions or dependencies. It never
sets up firmware/runtime drivers or changes node permissions. It refuses SSH
hints and wrong known NextUI paths; these checks do not attest against a local
user deliberately fabricating the environment. Only the normal Tools launch is
approved. The C entrypoint independently rejects SSH hints as defense in depth.

Only the owned `$USERDATA_PATH/RMXP-Video-Test/latest.log` is replaced per run;
final owned log-dir/log symlinks are refused. Process-local core dumping is disabled
and the file-size limit caps logs at 16 shell blocks (at most 16 KiB on intended
Linux shells). The parent UI's limits/settings are untouched. Excess library
logging can terminate this child by SIGXFSZ; that is FAIL, not clean-return proof.
No marker removal, device opens or log writes occur on the committed guarded path.

## Reproducible source-only host tests

From the repository root, with existing Python 3 and a C99 host compiler:

```sh
sh -n spikes/h700-video/Tools/h700/RMXP-Video-Test.pak/launch.sh
cc -std=c99 -Wall -Wextra -Werror -I spikes/h700-video/tests/include -fsyntax-only spikes/h700-video/triangle.c spikes/h700-video/tests/mock_api.c
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s spikes/h700-video/tests -v
git diff --check
```

Actual local result: **7 tests PASS**. Tests compile/run a temporary **host-only
mock API fixture**, which is deleted afterward. These are original minimal mock
API declarations, not vendored SDL/Khronos headers or an ABI substitute. No real
SDL/GL library is linked/loaded; no graphics process runs on the host or device.
The tests assert draw and swap calls, changing uniforms, exact simulated 5000-ms
exit, stuck/wrapping clock and event-flood behavior, stage failures and cleanup, own TERM/INT/QUIT,
SSH/backend rejection, bounded metadata/log file, symlink refusal, source-only
layout and rejection of the real x86 host ELF by the launcher. All shell-path
rewriting/metadata simulation is confined to temporary test copies. There is no
production test-root or mock-driver bypass. Static forbidden-call checks supplement
review; they are not a general shell security proof.

The dedicated `h700-video.yml` workflow runs these offline checks without any
artifact upload, package install or device access. ShellCheck runs only if already
available. Its actual GitHub status is reported on the PR separately.

## Precise blocked build and distribution plan

Do not use the declared `latest` image tag as a verified build input. A build owner
must first resolve every `UNKNOWN` affecting the candidate in provenance.json:

1. Record exact compiler/SDK archive checksum, toolchain image digest (if used),
   sysroot file manifest/hash, headers and library hashes/source/patches, build
   flags and target. The pinned Dockerfile **declares** a GCC 8.3 cross SDK release
   (recorded in JSON); that declaration is not verified archive provenance.
2. Identify installed AArch64 SDL, EGL/GLES and their transitive/`dlopen` libraries,
   PT_INTERP and GLIBC/GLIBCXX symbol floors from reviewed firmware/runtime inputs.
   Prefer read-only host ELF inspection of an agreed copy, never execute `ldd`
   against unknown executables, and do not modify/enable anything on the device.
   An SSH metadata session is allowed later; graphical execution from it is not.
3. Reconcile with [PR #19's STOP/GO gate](https://github.com/almighty-atlas/nextui-mkxp/blob/9d482dc981401166b40155678ad00e29daad9163/docs/DISTRIBUTION_GATE.md).
   Original app/launcher/mock files are MIT, which does not clear linked SDL or
   proprietary drivers. In particular the fork's
   [mali.h](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/mali.h#L1-L14)
   has a GPL-2.0-or-later notice; inspect complete fork/patch terms and the linked
   work's license/source obligations. Dynamic linking or relying on installed SDL
   does not automatically waive GPL obligations. Do not copy SDL/EGL/GLES libraries,
   vendor drivers, fonts or opaque release files into this package.
4. After those reviews, adapt this **unexecuted recipe**, with explicitly verified
   inputs. It is a command shape, not an existing reproducible H700 build:

   ```sh
   "$VERIFIED_AARCH64_CC" --sysroot="$VERIFIED_SYSROOT" -std=c99 -O2 -Wall -Wextra -Werror \
     -I"$VERIFIED_SDL_PREFIX/include" -I"$VERIFIED_GRAPHICS_HEADERS" \
     spikes/h700-video/triangle.c -L"$VERIFIED_SDL_PREFIX/lib" \
     -Wl,-Map,triangle.map -Wl,-z,noexecstack -o triangle -lSDL2 -lGLESv2 -lEGL
   "$VERIFIED_READELF" -h -l -d --version-info triangle
   ```

   No host include/library path fallback is permitted. Record the literal
   PT_INTERP, every DT_NEEDED and required symbol version from this **actual**
   artifact, reconcile the link map/driver `dlopen` closure and inspect output
   SHA-256. None of those actual binary facts is currently known. A direct EGL
   dependency must resolve to the same implementation SDL uses or the current
   display query can fail; do not guess paths from filename presence.
5. Only after independent code, provenance, legal and ABI review: prepare a new
   candidate with `launch.sh`, `bin/triangle`, this source, LICENSE and required
   third-party notices/source-delivery material, plus a checksum manifest. Remove
   the SOURCE_ONLY guard **only in that reviewed candidate**; never bypass it in
   this source template. Verify exact allowlisted archive paths, symlink/traversal
   exclusion, executable mode and ELF64/AArch64/loader compatibility. No binaries
   are packaged by this PR; no assembly or download script is supplied.

## One conditional owner test plan (future reviewed package only)

**This briefly owns the display, unlike the metadata probe. Never run the app or
launch.sh over SSH while NextUI is running.** No USB/SD reader or new service is
required. This plan is currently BLOCKED; no command below starts graphics.

1. After independent review and a cleared compatible candidate, verify the
   supplied checksum manifest and the exact allowlisted archive contents on your
   existing host. Confirm it contains no SDL/GPU libraries or game/assets and
   has the expected original source/notices. Keep the existing firmware/Paks.
2. Through the **already working SSH/file-transfer workflow**, copy only the
   reviewed `RMXP-Video-Test.pak` folder to the existing
   `/mnt/SDCARD/Tools/h700/` path. For example, with an already configured host
   alias, `scp -r reviewed/RMXP-Video-Test.pak DEVICE_ALIAS:/mnt/SDCARD/Tools/h700/`.
   If the destination already exists, stop instead of overwriting it. Do not
   install services, mount cards, edit `.system`, or copy to system partitions.
   File transfer is not a graphical launch. If mode preservation is needed, use
   the existing transfer tool's preserve-mode option; do not chmod devices/system.
3. On the handheld, select **NextUI > Tools > RMXP-Video-Test** once. Observe a
   moving multicolored triangle with correct orientation; an empty/clear-only
   screen, console log or invisible offscreen draw is insufficient. Let the app
   self-exit; do not depend on an untested MENU/POWER/button chord.
4. Confirm return to usable NextUI (display and navigation buttons responsive),
   and normal behavior afterward. A timeout, crash, missing triangle, wrong
   rotation or failed UI return is FAIL/UNPROVEN. Stop after the first failed
   stage; no privileged repairs, kernel changes, forced reboot or global kill.
5. Retrieve only `.userdata/h700/RMXP-Video-Test/latest.log` through the existing
   file-transfer method. Share only reviewed `RMXP_VIDEO` lines, removing any
   unexpected identifying text; do not append private system logs or env dumps.
   Report candidate/source checksum, model/firmware, visible animation/orientation,
   GL/EGL identity, exit code and return/navigation result to issue #22.

PASS requires **all**: visible animated shader triangle, identified hardware
renderer, and clean return to responsive NextUI. Code 0 alone is not PASS; unknown
or software renderer is UNPROVEN. Even PASS says nothing about audio, controller
mapping, engine startup, games or performance.

Rollback after a normally exited test: remove only the newly added
`Tools/h700/RMXP-Video-Test.pak` and, if desired after collection, its owned
`.userdata/h700/RMXP-Video-Test` diagnostics using existing file management.
Keep all other Paks, `.system`, user games, saves and settings. No automated removal
or recovery command is supplied. The currently committed source template is not
an install candidate.

## Evidence and unresolved acceptance

| Label | Current evidence |
| --- | --- |
| SOURCE_CONFIRMED | Pinned Mali-fbdev/ION/EGL design and synchronous NextUI Tools lifecycle; source hashes in JSON |
| HOST_PASS | C99 mock compilation, seven offline test methods with failure subcases, shell syntax, source-only layout and whitespace checks |
| OWNER_OBSERVED_H700 | Existing #1 metadata only; no new owner run requested |
| H700_RUNTIME_NOT_TESTED | Actual SDL init, resource access, accelerated shader output, rotation, timed exit and UI return |
| BLOCKED | Target toolchain/sysroot/installed-library identity, loader/symbol floor, legal/source-delivery review, target build/package and owner-run acceptance |

Read before implementation: required project docs, issue #22 and all comments,
PRs #19/#20/#21 source and discussion/review timeline (including #21's limited
spike authorization). The new files do not change those PR branches. Source
research rechecked NextUI init/toolchain settings, ION/pixmap requirements and
linked legal gate; it did not execute any firmware/build scripts. Compiler/tool
availability and missing development headers were inspected locally. Tests run
only against the mock fixture. No SSH connection, device operation, package
installation, network discovery, binary release or merge occurred.
