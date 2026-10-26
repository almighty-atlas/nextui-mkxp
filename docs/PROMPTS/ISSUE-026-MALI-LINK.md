# Zed/Codex-Folgeauftrag – Issue #26: authentisches H700 Mali-SDL/EGL/GLES-Linkinterface

**Repository:** `almighty-atlas/nextui-mkxp`  
**Arbeitsbereich:** bereits offener [PR #27](https://github.com/almighty-atlas/nextui-mkxp/pull/27), Branch `build/issue-26-linux49-mali`  
**Geprüfter Ausgangsstand:** `d678597ab6c9522594c1669a1f4eb3196fd63911`  
**Übergeordnetes Issue:** [#26](https://github.com/almighty-atlas/nextui-mkxp/issues/26)  
**Verboten:** Gerätezugriff, Geräteausführung, Firmwareänderungen, Binär-Uploads/Veröffentlichungen, PR-Merges und automatisches Schließen von Issues.

## Prompt zum Einfügen in Zed/Codex

```text
Repository: almighty-atlas/nextui-mkxp
Continue EXISTING Issue #26 and EXISTING PR #27 (branch
build/issue-26-linux49-mali). Do not open another issue or PR for
the same remaining issue scope. Start with git status and fetch
up-to-date remote branch; if head differs from
d678597ab6c9522594c1669a1f4eb3196fd63911, re-evaluate the
current evidence and do not overwrite concurrent changes.

OBJECTIVE
The Linux-4.9 libc/sysroot gate was already addressed in PR #27:
full private glibc 2.28 with Linux 4.9.170 headers and GNU ABI
note 4.9.0; libc-only AArch64 calibration executable linked;
original PR #23 triangle compiled to authentic AArch64 ET_REL.
Both CI workflows passed (32 + 13 offline tests).
DO NOT repeat the GNU Make 4.3/glibc rebuild as the primary task.

The sole immediate engineering target is the remaining independent
H700 Mali-fbdev graphics link gate. Prove a genuinely matched
AArch64 SDL2/EGL/GLES *development/link interface* if legally
and technically available, or document the precise irreducible
missing input without faking a successful link.

READ FIRST
- AGENTS.md and relevant project safety/provenance documents;
  Issues #1, #2, #3, #22, #24, #26; PRs #19, #20, #21, #23,
  #25, #27 (source, reviews, checks).
- PR #27 docs/build/issue-26-linux49-mali.md and evidence/inputs
  and scripts/issue_26_sysroot.py, issue_26_crosscheck.py,
  issue_26_sandbox.py, issue_26_test.py.
- PR #21 source-grounded Mali-fbdev ADR and the source-only
  triangle.c in PR #23 (pinned commit
  60721c1a81a9f54e507650f313a479ecaa9b6d2a).

SOURCE/PINNING
- NextUI H700 source at
  5291344b3aceae5fa197437a70824afb41e2d338.
- H700 toolchain recipe at
  04faa348c112617fc6b99be62308099ee6d43581.
- JohnnyonFlame SDL-malifbdev-rot at
  d4a7d7503524cc469fe775242f3f925d4dd56c88.
- Prior AArch64 libc investigation and private-build evidence
  from PR #27 head (not installed-device attestation).
- The device reports AArch64 Linux 4.9.170 and NextUI
  libSDL2-2.0.so.0.2800.5; this is OWNER-SUPPLIED METADATA,
  not a hash or proof of the installed ELF/driver.

STEPS
1. Construct an exact function/symbol/dependency matrix for
   the original C triangle.c:
   - SDL2 needed entrypoints and source fork declarations;
   - direct eglGetCurrentDisplay/eglQueryString and GLES2
     compile/shader/buffer/draw/swap entrypoints;
   - expected SONAME/NEEDED, possible SDL dynamic loading,
     Mali-fbdev vendor pixmap API, /dev/fb0 and /dev/ion;
   - real link-time vs runtime dependencies, and the distinction
     between native GLES2 symbols and SDL's EGL loader.
   Ground claims to immutable source locations, do not infer
   installed binaries from filenames.
2. Examine the pinned H700 recipe and source repositories
   for an authentic, auditable source-build path for the
   patched SDL2 2.28.5 library and an authorized AArch64
   EGL/GLES link interface. Prefer source/pinned headers and
   legitimate development import libraries over borrowed
   TrimUI SDK/PowerVR blobs. Do not invent or fabricate dummy
   .so/stub libraries that report success. Do not suppress
   undefined references or ignore DT_NEEDED closure.
3. If source/headers/build dependencies actually permit,
   BUILD SDL's H700 Mali-fbdev variant privately against the
   reviewed Linux-4.9-compatible sysroot; inspect the produced
   library ABI/SONAME, NEEDED, symbol exports, GNU ABI notes,
   and compiler/link maps. Confirm source/patch/license pins.
   Do not upload build outputs. If the SDL build requires
   proprietary headers or authenticated vendor .so files,
   isolate the first concrete requirement and stop that route.
4. Investigate provenance-reviewed H700 EGL/GLES *development*
   inputs from maintainers and published source/release
   manifests (e.g. NextUI/BaseOS H700 source/build recipes).
   If an eligible artifact exists: hash before extraction,
   inspect archives and licenses, and verify all AArch64
   symbol/version/NEEDED requirements offline. Do not copy
   unreviewed GPU/vendor binaries, do not release any.
   If unavailable, report a table of missing specific symbols,
   required SONAMEs/source IDs and why the linker cannot proceed.
5. Only when actual matching permissible inputs exist, attempt
   an isolated REAL link of the UNMODIFIED original triangle
   against the Linux-4.9 sysroot + verified H700 SDL/EGL/GLES
   dev inputs, then inspect PT_INTERP, NEEDED, RPATH/RUNPATH,
   GLIBC/GLIBC_PRIVATE needs, GNU Linux ABI note, load-time
   and SDL dlopen dependency closure. Include a complete link
   map and hashes. The test ELF must remain PRIVATE on host.
   A static linker PASS is not a functioning H700 graphics PASS.
6. Retain robust host isolation: clean explicit environment,
   pinned inputs/tools, no host-header/lib contamination,
   no lib/vendor copies into repo, no device/SSH operations,
   no root/system changes. Add tests for missing library
   inputs, bogus/host ELF, unexpectedly successful link with
   unreviewed inputs, and DLL/SONAME mismatch.
7. Harden the existing .github/workflows/issue-26-offline.yml
   only as appropriate: whitespace should cover the full PR
   base-to-head change set, including on push events, rather
   than silently relying on HEAD^ HEAD. Ensure docs/build
   issue-26 changes also trigger an offline check. Prefer a
   simple, reviewable implementation with explicit checkout
   history/base fetching. Preserve the pinned checkout and
   read-only permissions; DO NOT add a network-dependent CI
   toolchain build or artifact upload.
8. Update the existing Issue #26 report/JSON in PR #27;
   retain historical 87ca744 blocked experiment and the
   already successful libc progress. Include a clear matrix:
   LIBC49_BUILT, SDL_SOURCE_BUILT or SDL_BUILD_BLOCKED,
   EGL_GLES_LINK_INPUTS_VERIFIED or LINK_BLOCKED,
   TRIANGLE_HOST_LINKED or NOT_LINKED,
   ELF_POLICY_HOST_ONLY, H700_RUNTIME_NOT_TESTED,
   LICENSE_DISTRIBUTION_BLOCKED.
   Preserve source/host/owner/hardware evidence separation.
9. Respect licensing: the original C is MIT, while SDL's
   mali.h contains GPL notices, glibc has LGPL obligations,
   and proprietary EGL/GLES rights remain unresolved.
   Private build/testing does NOT authorize redistribution.
   Do not deem a release legally cleared without human review.
10. Verify changed-file diff, Python/JSON, offline tests and
    GitHub CI. Push ONLY to the current PR #27 branch and
    provide its new head SHA, CI run, actual source/host
    verification and smallest outstanding blocker.
    Keep PRs #19-#27 OPEN/UNMERGED; do not close #22/#24/#26.

STOP CRITERIA
No genuine, rights-reviewed development EGL/GLES library or
build route -> document LINK_BLOCKED with concrete needs and
stop. Never replace the unavailable library by PowerVR,
Mesa/glvnd, a fabricated stub, linker ignore flags or
an arbitrary vendor runtime copied from another device.
No device actions, graphics launch via SSH, ROM assets,
mkxp-z engine build or published H700 Pak.
```

## Übergabe und Entscheidungspunkt

Die Aufgabe darf keine Geräteinformationen nacherheben, keine NextUI-Laufzeit starten und keinen binären Test verteilen. Falls der Link an proprietären EGL/GLES-Entwicklungsdateien hängt, muss das als **konkreter, nachprüfbarer Blocker** zurückkommen. Ein späteres, gesondert freigegebenes read-only H700-Inventar wäre dann zu besprechen, aber nicht Bestandteil dieses Codex-Auftrags.
