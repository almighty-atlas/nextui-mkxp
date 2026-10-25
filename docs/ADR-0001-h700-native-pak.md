# ADR-0001: Conditional native RMXP Pak via H700 Mali-fbdev SDL/EGL

Date: 2026-10-25. Status: **PROPOSED; graphics feasibility BLOCKED pending one
reviewed smoke test**. Refs [issue #2](https://github.com/almighty-atlas/nextui-mkxp/issues/2).
This is source research and a design, not an implemented launcher or runtime.
No user commands or hardware actions are required at this stage.

## Decision and evidence vocabulary

Prefer **A: standalone AArch64 mkxp-z using an H700-compatible Mali-fbdev SDL2
backend and the device's EGL/GLES stack**, conditional on context creation,
visible rendering and clean return in the proposed smoke test. Do not require
KMS/DRM nodes, adopt R36S binaries, or substitute an ordinary upstream SDL build
without this backend. Keep B/C as alternatives, not validated fallbacks.

Use a visible `.rmxp` marker file in a top-level `(RMXP)` ROM folder, dispatched
to `Emus/h700/RMXP.pak/launch.sh` with the selected file as one argument. Marker
contents identify a stable per-game private directory; they are data, never shell
code. This discovery shape is **SOURCE_CONFIRMED** at the inspected NextUI pins;
the actual installed binary's behavior remains **NOT_TESTED**.

| Label | Meaning |
| --- | --- |
| SOURCE_CONFIRMED | Behavior read in the cited immutable source; not proof that an installed binary matches it |
| OWNER_OBSERVED_H700 | Owner-supplied metadata from [issue #1's sanitized report][H1]; not independently measured by Codex |
| HYPOTHESIS | Proposed integration behavior or inference awaiting verification |
| NOT_TESTED | No runtime evidence; specifically graphics, audio/input function, Pak lifecycle and save behavior |

## Baseline, source identity and concurrent changes

**OWNER_OBSERVED_H700:** RG35XX Pro; release-file `NextUI-20261013-0` / `39a06de`;
Base OS 1.4.0; Linux 4.9.170 aarch64; `/bin/sh` ELF64 little-endian AArch64;
MemTotal 996720 kB (~973 MiB); no swap. `/dev/fb0` was accessible, sampled DRM
nodes were absent/inaccessible; EGL/GLES2 and NextUI SDL2 `.2800.5` files were
present. These observations do not establish driver initialization, acceleration,
loader/glibc floor or SDL build identity. `/dev/ion` and Mali-specific resources
were not established by that probe. UI release confirmation is outstanding [H1].

This ADR starts from project main `99489ed0fe937ccec7be79949f496fd1abaeb3d9`.
PRs [#19][P19] (licenses) and [#20][P20] (probe/baseline) remain unmerged. This
change adds only this standalone ADR, leaving their branches and shared files
untouched. It does not duplicate `H700_BASELINE.md` or the license inventory.
The issue's requested insertion in `docs/ARCHITECTURE.md` is deferred, as the
issue prompt explicitly allows, until PR #20 is resolved; no issue is closed.

| Research source | Immutable revision / scope |
| --- | --- |
| NextUI reference requested by prompt | `5291344b3aceae5fa197437a70824afb41e2d338` [N1]–[N15] |
| NextUI release-file build hint resolved through GitHub | `39a06deadfdd2bd08209208ff40752c8e51a449d` [R1]; metadata match, not installed-file authentication |
| H700 toolchain recipe | `04faa348c112617fc6b99be62308099ee6d43581` [T1]–[T2], [N19]; independent research pin |
| SDL Mali-fbdev fork selected by that recipe | `d4a7d7503524cc469fe775242f3f925d4dd56c88` [S1]–[S6] |
| mkxp-z candidate from PR #19 audit | `37a04d14413454551a7b6aadbb4e93e67168accb` [M1]–[M4] |
| R36S reference | `b665091c1ff571a7a468bbf33af2f7c803c75220` [A1]–[A2] |
| Experimental NextUI mkxpz | `f25591e0f63bd0c772b5661c4318ea30aff4ce2f` [X1]–[X2], manifest version v0.6.7 |

An actual `git diff` between the full NextUI build-hint commit and the reference
pin was empty for PAKS.md, H700 init/launcher/makefile, frontend nextui.c,
common/utils.c and minarch/ma_environment.c. The citations below use the requested
reference pin. This narrows source-version uncertainty, but the recipe uses an
external toolchain image rather than locking its digest in NextUI [N19]; it does
not prove the installed SDL bytes match the independently pinned toolchain.
No release archives, toolchain images or vendor binaries were downloaded/run.

## Why framebuffer presence can coexist with accelerated GLES

**SOURCE_CONFIRMED:** the H700 startup exports `SDL_VIDEODRIVER=mali`, ALSA and
no-udev joystick hints, and selects EGL/GLES library candidates [N2]. Its launcher
prepends the bundled H700 libraries and calls that setup [N3]. The H700 makefile
stages an SDL described as `mali-fbdev`, built in the toolchain [N4]. The separate
recipe pins the SDL fork, applies an input patch, enables Mali/OpenGLES/shared SDL,
and explicitly disables KMSDRM, X11 and Wayland [T1]. No recipe was executed.

The backend has concrete GL hooks, not just a software framebuffer writer:

1. `MALI_bootstrap` registers the name `mali` and GL load/context/current/swap
   callbacks [S1]. Video init opens `/dev/fb0` **and `/dev/ion`**, reads framebuffer
   geometry, chooses rotation and normally initializes a blitter [S2]. Missing
   ION access can fail initialization even though fb0 is present.
2. Window creation forces `SDL_WINDOW_OPENGL`, loads EGL against
   `EGL_DEFAULT_DISPLAY`, and creates a surface. Default blitter operation uses
   ION/pixmap surfaces and vendor pixmap entrypoints; the no-blitter path uses a
   native fbdev window structure [S3]. This is a vendor EGL/fbdev route, distinct
   from DRM/GBM. Vendor EGL can require additional kernel resources; no claim is
   made that fb0 and ION alone are sufficient.
3. GL callbacks delegate to SDL EGL; default profile is GLES 2.0. Swap either
   calls EGL swap directly or coordinates the blitter/pixmap buffers [S4]. The
   blitter itself creates a GLES2 context and an EGL window surface [S5]. SDL's
   generic EGL loader respects EGL/GL-driver hints and loads libraries/symbols
   before obtaining a display [S6], [S8]. Library presence alone bypasses none of this.
4. NextUI H700 includes generic_video.c [N5]; it requests an OpenGL window and
   renderer and explicitly creates an ES 3.2 context in its non-desktop path [N6].
   That is source intent, **not evidence that the owner's installed binary
   obtained ES 3.2** or that mkxp-z should require that profile.
5. mkxp-z creates an SDL OpenGL window/context, resolves GL functions and draws
   using GL [M6]; its loader recognizes GLES and rejects major versions below 2
   [M1]–[M2]. Select the GLES profile (`gfx_backend=gles` / GLES driver hint) rather
   than desktop GL [M3]. A minimal ES2 test can establish this first context gate,
   but cannot establish all engine functions/extensions/shaders are supported.

**HYPOTHESIS:** linking a future AArch64 mkxp-z build to the compatible installed
H700 SDL ABI, inheriting the Pak's EGL/GLES environment, can create an accelerated
surface via this path without `/dev/dri/card*`. Verify the exact loaded libraries,
backend and GL strings on the device. Do not statically bundle mkxp-z's ordinary
SDL fallback and expect its KMSDRM configuration to substitute for `mali`.

**Software fallback decision:** direct fb0 CPU blitting could show a diagnostic
screen but does not provide mkxp-z's required GL context. A software GL rasterizer
would add a separate renderer, licensing/dependency burden and unmeasured CPU/RAM
cost on ~973 MiB hardware. It is not a useful accepted RGSS performance fallback
without measured evidence. If Mali context creation fails, STOP and diagnose;
do not silently claim success through software rendering or change firmware.

## Candidate comparison

| Candidate | Source basis / graphics | Lifecycle, controls and costs | Decision |
| --- | --- | --- | --- |
| A. Native standalone mkxp-z | SDL GL/GLES engine [M1]–[M3]; H700 Mali-fbdev path above | NextUI exits its UI then waits for child; wrapper owns clean exit, SDL/audio cleanup, per-game state. Patched SDL input layout matters [T2]; audio still requires mkxp-z/OpenAL review. No standard NextUI menu/save states/instant resume | Conditional preference; graphics + ABI + licenses still BLOCKED |
| B. mkxp-z libretro + alternative GL-capable frontend | Requires an identified core, pinned source and a proven GL frontend on H700; these inputs are UNKNOWN here | Adds another frontend/control/config lifecycle, still needs the same working native GPU path. More dependencies and no automatic NextUI integration | Defer; not a shortcut around the surface problem |
| C. PortMaster-derived / experimental NextUI mkxpz approach | Experimental manifest v0.6.7 lists **tg5040/tg5050 only**; repository has README + pak.json, no reproducible launcher/source [X1–X2] | README says unstable. Actual GPU setup, exit behavior, game discovery and binary provenance UNKNOWN. PortMaster packaging ideas need H700/NextUI-specific adaptation | Research lead only; no opaque binary download, execution or import |

**MinArch nuance:** PAKS.md says the GL libretro API is unsupported [N21]. The
inspected MinArch source does contain a `SET_HW_RENDER` handler returning true,
but only logs/adjusts the requested type/version; it does not establish the
framebuffer/proc-address/context-reset callback contract [N7]. Searching MinArch
for those callbacks found no implementation. NextUI using GLES internally is
not evidence of usable GL libretro support. Do not route a GL core through
MinArch based on that handler, or label a replacement frontend/core available.

**R36S contrast:** its script enables SDL KMSDRM/shared driver loading and ALSA
on an ARMv7/armhf gcc-9 target [A1]; its launcher uses ArkOS paths and CPU-governor
changes [A2]. That solves a different native-window/ABI problem. Patches, exitwatch
ideas and settings are reference material only, with PR #19's provenance gates.
No R36S armhf library, governor/zram recipe or binary is approved for H700.

## Discovery and quoting contract

The following is **SOURCE_CONFIRMED**, with no H700 menu run claimed:

| Question | Pinned behavior / design consequence |
| --- | --- |
| How is `(RMXP)` resolved? | `getEmuName` extracts the **first folder below ROMS_PATH**, then its parenthesized tag. Nested game directories do not change that console tag. External `Emus/<platform>/<tag>.pak/launch.sh` is preferred over built-in fallback [N8] |
| What appears in the browser? | Console directory needs a matching emulator and at least one non-hidden entry [N9]. `addEntries` labels ordinary files ENTRY_ROM without an extension allowlist; directories become ENTRY_DIR, except `.pak` directories become ENTRY_PAK [N10]. Dot files, `.disabled` and `map.txt` are hidden; optional map.txt aliases can additionally hide entries [N11], [N16] |
| Is `Game.ini` selectable? | A non-hidden ordinary `Game.ini` is an ENTRY_ROM; it has no special meaning to NextUI. Opening it passes its filename to the selected Pak [N10], [N12]. Browsing all game contents would expose many unrelated files and repeated `Game.ini` labels, so markers are preferable |
| Does a game directory auto-launch? | Normally it opens a directory; special same-name cue/m3u auto-launch handling exists [N13]. There is no Game.ini auto-launch rule. A `.pak` directory directly invokes its own launch.sh without a ROM argument [N22]; that would duplicate a launcher per game and is not the chosen model |
| Can `.rmxp` markers work? | Yes at the source-dispatch level: ordinary non-hidden files are ROM entries, no core extension check. NextUI passes the path without interpreting contents [N10], [N12]. Marker parsing is our proposed wrapper contract, not an upstream file format |
| Are spaces handled? | Frontend single-quotes launcher/ROM paths, escapes embedded apostrophes in place, queues a command via `/tmp/next`; parent evals it after UI exit [N12], [N17], [N14]. A real H700 emulator-Pak example stores `ROM="$1"` and quotes it [N15]. Wrapper must independently quote every argument and never eval a marker |

There are fixed 256-byte command/path buffers and in-place quote expansion in the
frontend [N12], [N14]. Do not claim arbitrary-length/unusual filenames are safe.
Use short ASCII marker filenames with spaces supported, no apostrophes/newlines
or shell syntax in the initial profile, and keep the complete generated command
well below 256 bytes (initial policy: at most 200 bytes including quoting).
The hook parser uses simple quote-based sed extraction [N18]; apostrophe handling
in hooks needs separate verification despite dispatch's escaping. This is a
compatibility limit, not a reason to rename or modify existing game files.

## Minimal reversible layout and two-game data contract

**HYPOTHESIS / design only:** no directories, game content or launcher are created
by this PR. A future reviewed install contains only redistributable engine code,
reviewed resources/notices and this wrapper; user games remain separately supplied.

```text
/mnt/SDCARD/
  Emus/h700/RMXP.pak/
    launch.sh                 one wrapper, executable; engine path relative to Pak
    bin/mkxp-z                future reviewed AArch64 build only
    LICENSES/                 corresponding notices/source/relink instructions
  Roms/RPG Maker XP (RMXP)/
    Example One.rmxp          data: rmxp-v1:game-one
    Example Two.rmxp          data: rmxp-v1:game-two
  .userdata/h700/RMXP/games/
    game-one/
      content/Game.ini        privately installed user game, with Data/ etc.
      home/                   per-game HOME/XDG preference/configuration state
      logs/                   bounded diagnostics, no full game paths/payloads
    game-two/
      content/Game.ini        separate private game instance; same names allowed
      home/
      logs/
```

For one game omit the second marker/tree; adding it must not overwrite the first.
A stable id `[a-z0-9][a-z0-9-]*` (max 48 characters, no `..`, slash or whitespace)
is assigned by the owner, independent of filename, title and SD mountpoint.
Marker is exactly one bounded line with that version/id, optionally trailing LF;
reject duplicates/extra fields/absolute paths/symlink escapes. Resolve only beneath
`$USERDATA_PATH/RMXP/games/<id>` after validating inherited H700 paths; no network,
search through unrelated files, downloaded games or arbitrary executable paths.
The marker's parser and canonical-path policy still require implementation/tests.

Set per-game HOME and XDG roots, configure the engine's preference organization/
application identifiers deterministically, and run with the private `content/`
as cwd. mkxp-z reads config and Game.ini and can change gameFolder [M4]; its preference
path otherwise falls back to the game's title [M5], so titles alone cannot provide
isolation. Do not assume passing Game.ini as a positional engine argument selects
a game: the **wrapper consumes the marker**, validates it, then sets config/cwd.

Save isolation means separate **private game instances**, not a claim that all
Ruby saves obey XDG/HOME. Relative game-script saves may remain inside that
instance's content directory; preserve them. Arbitrary absolute-path script writes
cannot be redirected or sandboxed by setting HOME. Game-specific save paths and
migration/import of existing saves remain a gate; never relocate, quarantine,
overwrite or delete user originals automatically. This costs SD-card space for
private instances, not duplicated engine RAM; users install their own files.

Missing marker/id/Game.ini/Data directory, unknown ABI or unwritable user root:
report a bounded actionable error, exit nonzero, create no partial replacement
and return to NextUI. Before launching, validate all inputs; create only owned
per-game state after success. No engine-bundle writes, system mounts, firmware,
sudo, zram, sysctl, clock/governor or globally exported environment changes.

## Lifecycle, exit and rollback

**SOURCE_CONFIRMED:** queueNext writes `/tmp/next` and quits the UI [N17]. The
H700 parent loop runs nextui.elf, evaluates the queued command synchronously,
runs hooks, removes its queue file and starts the UI again while its execution
marker remains [N14]. Thus the wrapper should keep the engine in the foreground,
wait for its own child and propagate a useful exit result; no detached engine or
second framebuffer owner. Do not modify `/tmp/nextui_exec`, start another NextUI,
source its init script or duplicate its global system setup. Existing NextUI
hooks/governor behavior belongs to that parent; the Pak adds none.

**HYPOTHESIS:** future engine/wrapper handles SDL_QUIT/its own TERM/INT, destroys
GL context/window, quits audio/SDL, reaps only its own child and returns. An explicit
reviewed SDL input exit action is needed; MENU/POWER/SELECT+START are not assumed
universal or borrowed from R36S evdev. No grabs of private input streams and no
killall. NextUI UI restart does not by itself prove video/audio restoration.
There is no promise of save states, standard menu, game switcher, quicksave or
instant resume [N1].

Rollback: exit through the approved method; remove only the newly installed
`Emus/h700/RMXP.pak` and owned `.rmxp` markers via normal file management. Keep all
`.userdata/h700/RMXP/games/*`, saves and original games. No change to `.system`,
existing Paks or firmware to undo. Removal/migration of private data is a separate
explicit owner decision. This rollback has not been executed on H700.

## ONE-SMOKE-TEST proposal: game-free SDL Mali/GLES handoff

**PROPOSAL / NOT_TESTED.** Separate reviewed work after ADR approval; not an engine
build and no user action now. One test package `Tools/h700/RMXP-Video-Test.pak`
with original procedural graphics and a small source-available native test app;
no Ruby, RGSS, RTP, fonts, downloaded sample games, audio playback or third-party
opaque binaries. Choose explicit GPL-compatible source terms after reviewing
all linked dependencies. Do not redistribute stock EGL/GLES/GPU blobs. Legal
review in PR #19 must additionally consider the fork's GPL-noticed `mali.h` [S7];
root SDL Zlib terms alone do not clear every bundled backend file.

Before device use: pin/review the app source/toolchain/sysroot/digest, library ABI
and source/notice obligations; statically inspect ELF/interpreter/NEEDED and symbol
requirements against the agreed installed runtime. Owner reviews the package and
expected transient display use. No full mkxp-z build, copying R36S patches or
installation of tools on the device.

Single test sequence through the **normal NextUI Tools entry**, with no concurrent
SSH display process and no firmware init replay:

1. Record only compiled/linked SDL versions, driver names and process-local
   EGL/GLES resolution metadata; no environment dump, network or private paths.
   Use the already installed H700 SDL and inherited `mali`/EGL hints. If the Mali
   backend is missing or required resource access fails, log the stage and STOP.
   Do not chmod nodes, install drivers or switch to KMS/software as an automatic
   fallback. Run without requesting privilege elevation.
2. Initialize only video/timer, set an ES 2.0 profile **before** creating one
   640×480 SDL_OPENGL window, create/make-current a context, resolve required GLES
   functions and record GL_VENDOR/RENDERER/VERSION/GLSL. Check errors at each stage.
   Keep the backend's existing default blitter/rotation behavior for this first
   test; do not try multiple backend configurations in one opaque pass.
3. Compile original minimal shaders and display a changing colored triangle for
   at most five seconds via real draws and SDL_GL_SwapWindow. A clear-only frame,
   library load or successful SDL_Init alone is insufficient. Owner confirms a
   visible correctly oriented image, not just offscreen/pbuffer success. A known
   software renderer or unidentified renderer yields acceleration **UNPROVEN**.
4. Auto-exit without input dependency; accept SDL_QUIT/own TERM gracefully. Delete
   GL objects/context/window and SDL state, return to the waiting wrapper, then
   confirm NextUI UI/display/buttons are usable again with no surviving test
   process. Record stage/result and exit code in one bounded owned test log.
   A separately reviewed watchdog may signal only this child after ten seconds;
   it cannot guarantee recovery from a kernel/driver hang. If rendering/return
   hangs, stop testing; no force-reboot or global kill command in the package.

The test temporarily opens GPU/display resources and renders; it is **not the
read-only metadata probe**. It makes no persistent firmware/configuration, mount,
kernel, governor, zram, brightness or volume changes. Any backend display-state
side effect must be observed/restored on normal exit; failure to return cleanly
is FAIL, not permission to run global repair scripts. Remove only its test Pak
and owned diagnostic log after review.

| Outcome | Gate consequence |
| --- | --- |
| Loader or SDL/mali unavailable | FAIL; identify exact compatible source/runtime before another reviewed attempt |
| Context created but no visible output, software/unknown acceleration, wrong orientation, or dirty return | FAIL/UNPROVEN; isolate backend/presentation/cleanup issue |
| Visible GLES shader draw, identified hardware renderer, clean timed return and responsive UI | PASS for this narrow video/lifecycle gate only |
| Engine initialization, shaders/extensions at game load, input mapping, OpenAL/audio, saves and games | Still NOT_TESTED after this test; separate later acceptance |

## Gates and next step

| Gate | Current state / required evidence |
| --- | --- |
| Upstream marker-file discovery/tag/argument/lifecycle contract | SOURCE_CONFIRMED for both inspected NextUI commits; real installed behavior NOT_TESTED |
| Owner H700 metadata | OWNER_OBSERVED_H700; #1 still open for remaining ABI/runtime acceptance |
| Mali-fbdev/EGL source route | SOURCE_CONFIRMED capability path; installed SDL identity, ION/vendor resources, context/presentation and clean return NOT_TESTED |
| Exact libc/interpreter/symbol floor and toolchain/dependency lock | BLOCKED; metadata is insufficient |
| Code/binary redistribution including backend and dependencies | BLOCKED by unresolved provenance/license obligations; PR #19 remains authoritative pending review |
| Per-game save behavior, exit mapping and game compatibility | HYPOTHESIS / NOT_TESTED; no supported-game claim |
| Shared architecture/compatibility/test-plan integration | Deferred to avoid conflicting with PR #20; ADR linked from this PR |

Next unblocked step: review this ADR and its source evidence. If accepted, prepare
**only the one game-free video test above** in separately reviewed work with exact
source/ABI/license inputs; gather real video/return evidence before an engine
cross-build decision. Do not start Issue #4 or mark #2 complete from this document.

## Commands and static verification evidence

Executed in cloud, with sanitized source metadata only:

```sh
git fetch origin
git worktree add -b docs/issue-2-h700-architecture /workspace/nextui-mkxp-issue2 origin/main
# In separate research directories, not the project tree:
git clone --depth 1 https://github.com/LoveRetro/h700-toolchain.git /workspace/scratch/h700-toolchain
git clone --filter=blob:none https://github.com/JohnnyonFlame/SDL-malifbdev-rot.git /workspace/scratch/SDL-malifbdev-rot
git -C /workspace/scratch/SDL-malifbdev-rot checkout d4a7d7503524cc469fe775242f3f925d4dd56c88
git clone --depth 1 https://github.com/KrutzOtrem/nextui-mkxpz.git /workspace/scratch/nextui-mkxpz
git -C /workspace/scratch/NextUI fetch origin 39a06deadfdd2bd08209208ff40752c8e51a449d
```

Reproducible document-only checks from the project root (no network):

```sh
git diff --check
python3 - <<'PY_CHECK'
from pathlib import Path
import re
p = Path('docs/ADR-0001-h700-native-pak.md')
s = p.read_text()
refs = dict(re.findall(r'^\[([^]]+)\]: (\S+)$', s, re.M))
used = set(re.findall(r'\[([A-Z][A-Z0-9]+)\](?!\()', s))
assert used <= refs.keys(), used - refs.keys()
assert len(re.findall(r'^```', s, re.M)) % 2 == 0
for url in refs.values():
    if '/blob/' in url:
        assert re.search(r'/blob/[0-9a-f]{40}/.+#L[0-9]+-L[0-9]+$', url)
print('PASS: document references, immutable citation syntax and fences')
PY_CHECK
```

The audit additionally ran `python3 /workspace/scratch/check_issue2.py`, comparing
all pinned citation paths/line bounds with the cloned checkout and verifying its
HEAD matched each cited commit: **41 file/line citations; 45 reference definitions**.
This check validates source locations, not the truth of a runtime hypothesis.

The initial `git fetch origin 39a06de` failed because it was not a remote ref;
GitHub `github_fetch_commit` resolved the full commit, whose fetch succeeded.
`git diff` for the selected NextUI files listed above returned empty.
`rg`, `nl -ba`, `sed` and `git show` inspected the cited files, required project
documents, PR #20 baseline and R36S recipe/launcher; connector reads inspected
issues #1/#2 and their comments, active PRs #19/#20 and the task prompt.

| Verification | Level / actual result |
| --- | --- |
| `git diff --check` / staged whitespace check | STATIC PASS |
| Python validation of pinned citation file/line bounds, Markdown reference resolution and local links | STATIC PASS; exact source snippets read for claims; not a runtime test |
| Source-contract comparison of release-hint/reference files | STATIC PASS (empty diff for selected files); not installed binary attestation |
| Engine, frontend, toolchain build; smoke-test implementation/execution | NOT_TESTED; none performed |
| Device access, graphics/audio/input/Pak lifecycle | NOT_TESTED by Codex; only linked owner metadata used |

No code, workflow, assets, binaries or modifications to existing documents are
included. Static checks do not establish hardware feasibility or legal clearance.

## Pinned source citations

[N1]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/PAKS.md#L3-L25
[N2]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/bin/h700-init.sh#L24-L47
[N3]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/MinUI.pak/launch.sh#L4-L38
[N4]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/h700/makefile#L23-L42
[N5]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/h700/platform/platform.c#L1013-L1014
[N6]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/common/generic_video.c#L652-L692
[N7]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/minarch/ma_environment.c#L388-L405
[N8]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/common/utils.c#L352-L385
[N9]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/nextui/nextui.c#L676-L699
[N10]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/nextui/nextui.c#L1003-L1036
[N11]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/common/utils.c#L36-L38
[N12]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/nextui/nextui.c#L1267-L1329
[N13]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/nextui/nextui.c#L1444-L1461
[N14]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/MinUI.pak/launch.sh#L136-L166
[N15]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/Emus/GB.pak/launch.sh#L1-L14
[N16]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/nextui/nextui.c#L242-L297
[N17]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/nextui/nextui.c#L1086-L1125
[N18]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/MinUI.pak/launch.sh#L116-L129
[T1]: https://github.com/LoveRetro/h700-toolchain/blob/04faa348c112617fc6b99be62308099ee6d43581/support/build-sdl2.sh#L11-L64
[T2]: https://github.com/LoveRetro/h700-toolchain/blob/04faa348c112617fc6b99be62308099ee6d43581/support/sdl2-h700.patch#L23-L40
[S1]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_malivideo.c#L79-L114
[S2]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_malivideo.c#L135-L175
[S3]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_malivideo.c#L411-L484
[S4]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_maliopengles.c#L30-L93
[S5]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_maliblitter.c#L79-L137
[S6]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/SDL_egl.c#L338-L415
[S7]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/mali.h#L1-L14
[M1]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/main.cpp#L771-L810
[M2]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/display/gl/gl-fun.cpp#L77-L115
[M3]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/meson.build#L50-L68
[M4]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/config.cpp#L234-L267
[M5]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/config.cpp#L424-L430
[A1]: https://github.com/Periko21/mkxp-z-r36s/blob/b665091c1ff571a7a468bbf33af2f7c803c75220/build/03-source-and-patches.sh#L60-L95
[A2]: https://github.com/Periko21/mkxp-z-r36s/blob/b665091c1ff571a7a468bbf33af2f7c803c75220/launcher.sh#L14-L41
[X1]: https://github.com/KrutzOtrem/nextui-mkxpz/blob/f25591e0f63bd0c772b5661c4318ea30aff4ce2f/pak.json#L1-L16
[X2]: https://github.com/KrutzOtrem/nextui-mkxpz/blob/f25591e0f63bd0c772b5661c4318ea30aff4ce2f/README.md#L1-L1
[N19]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/makefile.toolchain#L14-L42
[R1]: https://github.com/LoveRetro/NextUI/commit/39a06deadfdd2bd08209208ff40752c8e51a449d
[H1]: https://github.com/almighty-atlas/nextui-mkxp/issues/1#issuecomment-6403001093
[P19]: https://github.com/almighty-atlas/nextui-mkxp/pull/19
[P20]: https://github.com/almighty-atlas/nextui-mkxp/pull/20
[M6]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/main.cpp#L222-L240
[N21]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/PAKS.md#L105-L107
[S8]: https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/SDL_egl.c#L557-L570
[N22]: https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/workspace/all/nextui/nextui.c#L1220-L1231
