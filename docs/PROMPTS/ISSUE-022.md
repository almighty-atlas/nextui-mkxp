# Codex task — Issue #22: game-free H700 Mali-fbdev graphics smoke test

**Repo:** `almighty-atlas/nextui-mkxp`  
**Task:** [Issue #22](https://github.com/almighty-atlas/nextui-mkxp/issues/22)  
**Status:** pre-engine feasibility spike; research in [PR #21](https://github.com/almighty-atlas/nextui-mkxp/pull/21) is **PROPOSED**, not validated on hardware.

## Codex master prompt (copy into Codex)

```text
Repository: almighty-atlas/nextui-mkxp
Work exclusively on GitHub Issue #22:
[M0 SPIKE] Prove Mali-fbdev SDL2/GLES2 rendering and clean NextUI return on H700.

Start by inspecting AGENTS.md, README.md, docs/ROADMAP.md,
docs/CODEX_WORKFLOW.md, docs/SOURCES.md, docs/TEST_PLAN.md,
Issue #22 (all acceptance criteria), and PRs #19/#20/#21 including
their source and review comments. Read the ADR in PR #21 directly
from branch docs/issue-2-h700-architecture. Do not claim its
hardware assumptions were verified. All three PRs remain unmerged;
avoid changing files they already touch, and do not merge them.

Objective: create a tiny, ORIGINAL-source, game-free H700 Mali-fbdev
SDL2 + OpenGL ES 2.0 video feasibility test, not a mkxp-z build.

1. Verify pinned upstream NextUI H700 launcher, SDL mali-fbdev
   backend, init and toolchain sources. Determine exactly how the
   *already installed* H700 SDL/EGL/GLES path is meant to work.
   Inspect ION/pixmap/vendor resource requirements and dynamic
   linking/ABI expectations. Treat the user's Base OS 1.4.0 /
   NextUI-20261013-0 / kernel 4.9.170 AArch64 data as
   OWNER_OBSERVED_H700 metadata, not proof of working GLES.
2. Write minimal original C code: SDL_Init(video and timer),
   ensure the intended SDL video backend is 'mali', request GLES2,
   create one 640x480 SDL_WINDOW_OPENGL, create/make current context,
   compile/link simple in-memory GLES vertex and fragment shaders,
   draw one animated colored triangle, swap real display buffers
   for max 5 seconds, emit bounded privacy-safe stage logs,
   free all GL/SDL resources and exit with diagnostic code.
   A clear-only frame or successful SDL_Init is not a PASS.
3. Design the corresponding minimal, reversible
   Tools/h700/RMXP-Video-Test.pak launcher for normal NextUI Tools
   handoff. It must run in the foreground and allow NextUI to
   return on normal exit. A safe time limit/owner-specific
   watchdog can be designed; never use global killall, reboot,
   sudo, firmware scripts, sysctl, zram, governors or chmod
   on system/device nodes. No game or asset files.
4. Pin *actual* toolchain, libraries, sysroot and source commits
   as far as verifiable. Before any redistributable binary,
   reconcile GPL/LGPL/SDL Mali-fork and its GPL-noticed mali.h
   with the project distribution STOP/GO gate in PR #19.
   Never vendor unapproved SDL/driver binary blobs or use
   a mismatched host/x86_64 executable in an H700 archive.
   If a legally clean compatible H700 build is impossible now,
   deliver a precise SOURCE-ONLY build plan + static tests,
   document BLOCKED, and do not create or upload a binary.
5. Implement useful offline host/static tests: POSIX shell syntax,
   package layout when applicable, no forbidden writes/process
   management, deterministic bounded timeout, source/symbol
   architecture checks when applicable. Distinguish HOST tests
   and H700 results. Tests cannot prove physical screen output.
6. Produce ONE clear owner manual test plan, only after the package
   has been independently reviewed: how to copy the reviewed
   package via the existing SSH/file workflow (no USB/SD reader),
   launch it through NextUI > Tools, observe moving triangle and
   correct rotation, let the tool self-exit, verify NextUI
   responsiveness, and return sanitized stage logs.
   IMPORTANT: unlike the earlier read-only probe, this briefly
   takes over the display. It must NEVER be launched over SSH
   while NextUI itself is running.
7. Do not test on the owner's handheld, do not enable services,
   modify system directories or user's data, install packages
   on the handheld, or start issues #4/#5/#6/#7.
8. Create an issue-scoped branch and unmerged PR linking #22.
   Include exact commands/results, provenance/licenses, changed
   files, tests/CI, risks and rollback, and an explicit matrix:
   SOURCE_CONFIRMED / HOST_PASS / OWNER_OBSERVED_H700 /
   H700_RUNTIME_NOT_TESTED / BLOCKED. If stuck, report the
   first concrete blocker instead of fabricating success.

Do not merge, do not auto-close #22, and do not claim mkxp-z or
Pokémon Infinite Fusion/Decay compatibility from this test.
```

## Required test gate

A future test is a PASS **only** if the actual owner's H700 produces a visibly animated shader-drawn triangle with an identified GPU renderer **and** returns cleanly to functional NextUI. A runtime failure must remain documented and should not trigger automatic fallback/privileged remediation.

## Current preflight

- AArch64 ELF64 shell: owner observed
- EGL/GLES and NextUI SDL2 libraries: present only
- Mali-fbdev route: source identified in PR #21
- `/dev/ion`, vendor pixmap, EGL context and actual screen draw: NOT_TESTED
- Linked library provenance / released binary distribution: BLOCKED pending review
- Physical game-free GLES2 test: NOT_TESTED

Game files, proprietary assets, third-party opaque runtime ZIPs, and all firmware/driver changes are outside scope.
