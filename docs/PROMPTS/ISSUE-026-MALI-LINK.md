# Zed/Codex – Issue #26, Fortsetzung von PR #27 nach `bcba27f`

**Repository:** `almighty-atlas/nextui-mkxp`<br>
**Bestehender PR:** [#27](https://github.com/almighty-atlas/nextui-mkxp/pull/27), Branch `build/issue-26-linux49-mali`<br>
**Ausgangspunkt:** `bcba27f76a3fe4d8aecfebdd81cc613768e3c4d2` (vor dem Start auf neuen HEAD prüfen)<br>
**Scope:** ausschließlich Quellen-/Host-Build-Experimente, Tests und Dokumentation. **Kein H700-Zugriff, keine Geräteausführung, keine veröffentlichten Binärdateien, keine Merges.**

## Aktueller Befund

- PR #27 enthält bereits den vollständig neu gebauten **Linux-4.9-Sysroot / glibc 2.28** aus dem früheren Host-Experiment, ein libc-only AArch64-Kalibrierungs-ELF und das **unveränderte** Dreieck aus PR #23 als AArch64-Objekt. Diese Resultate dürfen nicht mit einem H700-Test verwechselt werden.
- Die folgenden SDL-Mali-Vorbereitungen erreichten `SDL_BUILD_BLOCKED`: Der private Sysroot war in der neuen Cloud-Session nicht vorhanden; der neue native Bootstrap scheiterte mit GNU **M4 1.4.20** in `_Generic`-Fehlern. `LINK_BLOCKED` bleibt separat.
- **Neu verifizierte Lösungsquelle:** GNU [M4 **1.4.21**, Release 2026-02-06](https://lists.gnu.org/archive/html/info-gnu/2026-02/msg00004.html) behebt laut Maintainer genau Konflikte mit neueren glibc-/C23-`_Generic`-Deklarationen. Offiziell gemeldeter SHA-256 für `m4-1.4.21.tar.xz`:
  `f25c6ab51548a73a75558742fb031e0625d6485fe5f9155949d6486a2408ab66`.
  URL: `https://ftpmirror.gnu.org/m4/m4-1.4.21.tar.xz`; optionale Signatur `.sig`. Hash vor Entpacken unabhängig prüfen; Release-Checksum allein ist noch kein erfolgreich geprüfter Download.
- **Neu geprüfte H700 SDL-Quelle:** In [`SDL_malivideo.c`](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_malivideo.c#L90-L96) wird `GL_GetProcAddress` auf `MALI_GLES_GetProcAddress` gesetzt. Das [Mali-GLES-Header-Mapping](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_maliopengles.h) definiert dies als `SDL_EGL_GetProcAddress`. SDL [dokumentiert](https://wiki.libsdl.org/SDL2/SDL_GL_GetProcAddress), dass GL-Funktionen nach dem Kontextaufbau über `SDL_GL_GetProcAddress` aufgelöst werden können. **Damit ist zu prüfen, ob die direkten GLES2-/EGL-Abhängigkeiten des SPIKE-Programms entfallen können.** GLES/EGL bleiben zur Laufzeit erforderlich.

## Aktueller Codex-Master-Auftrag

```text
Repository: almighty-atlas/nextui-mkxp

Continue ONLY existing Issue #26 and PR #27, branch
build/issue-26-linux49-mali. Re-read AGENTS.md, source/provenance
rules, all comments on PR #27, PR #19 licensing gate, PR #21
Mali-fbdev ADR, PR #23 original source and tests, current PR #27
reports and CI. Fetch and inspect current remote branch head; do
not discard work or rebase/merge other PR branches.

GOAL: investigate TWO narrow, independent solutions:
A) GNU M4 1.4.21 for the blocked native source-tool bootstrap;
B) SDL-only direct linking for an alternative game-free GLES2
triangle using SDL_GL_GetProcAddress rather than direct EGL/GLES2
imports. We want a reproducible private-host proof, or an exact
first blocker; not more unsourced general speculation.

PHASE A — SOURCE-VERIFIED M4 CORRECTION
1. Inspect the precise m4 1.4.20 build log and host compiler/glibc
   facts in PR #27. Compare the exact _Generic/bsearch/memchr
   failures with GNU M4 1.4.21 official release announcement
   (2026-02-06). Verify that 1.4.21 is applicable, not merely
   newer, and make no unsupported assertion about GCC flags.
2. If safe: acquire m4-1.4.21.tar.xz from the OFFICIAL GNU
   release; verify actual bytes against maintainer-published
   SHA256 f25c6ab51548a73a75558742fb031e0625d6485fe5f9155949d6486a2408ab66
   BEFORE inspection/extraction. Check archive paths/symlinks,
   check license; optionally verify trusted maintainer GPG
   signature. Build private native m4 and run a narrow smoke
   (`m4 --version`, basic deterministic macro expansion).
   Do not install anything globally or commit the executable.
3. Change only the pinned M4 host-tool input in the isolated
   sysroot/SDL preparation recipe when confirmed; don't change
   target glibc/kernel baseline or quietly alter source flags.
   Existing successful 4.9-sysroot build evidence is retained.
   Rebuild the private sysroot only if this new ephemeral host
   does not have the previously reviewed private output, and
   mark this as a new experiment, not new H700 evidence.
4. If feasible, reach actual SDL 2.28.5 configure and source
   build using pinned H700 fork and H700 patch; inspect real
   AArch64 SDL ELF, SONAME, NEEDED, RPATH, exported SDL APIs,
   glibc/kernel notes, dynamic EGL/GLES loader and dependencies.
   The H700 SDL Mali fork includes GPL-noticed source: PRIVATE
   host build != permission to ship a library or binary.
   Any authentic proprietary GPU development/link input absence
   remains BLOCKED; never fabricate replacement vendor libraries.

PHASE B — A MORE DIRECT WAY AROUND LINK-TIME GLES/EGL
5. Review original triangle.c at PR #23 pinned head
   60721c1a81a9f54e507650f313a479ecaa9b6d2a
   and its real 19 SDL / 2 EGL / 26 GLES2 calls. Explore a
   separate EXPERIMENTAL variant inside the private host
   workspace, without overwriting or editing PR #23 source:
   - Keep original functional draw/animated triangle, shader
     compile/link checks, cleanup, signal/timeout, metadata
     safety and strict failure codes.
   - Get GL entrypoints via correctly typed GL function pointers
     returned by SDL_GL_GetProcAddress AFTER a successfully
     created/current GLES2 context. Verify non-null pointers and
     GLES2 version/profile, and use actual shader draw, not
     glClear-only/no-op behavior.
   - Consider removing direct eglGetCurrentDisplay /
     eglQueryString calls for the feasibility spike; log
     GL_VENDOR / GL_RENDERER / GL_VERSION via glGetString and
     SDL driver identity. If EGL-specific diagnostics remain,
     explicitly research a legitimate separately loaded EGL
     handle; do not assume SDL_GL_GetProcAddress exposes core
     eglQueryString, and do not treat optional EGL metadata as
     GPU proof.
   - Use SDL2 as the ONLY directly linked video library IF the
     native linker/ELF evidence permits; allow target runtime SDL
     to dynamically load the actual EGL/GLES implementation.
   - No dummy GLES/EGL stubs, static vendor imports, PowerVR/Mesa
     substitution, forced unresolved symbols or omission of
     required GL calls. Keep an explicit original-vs-variant
     source and ABI delta.
6. If a matching AUTHENTIC SOURCE-BUILT SDL library exists and
   the variant compiles/links against it in the verified private
   Linux-4.9 sysroot, run native readelf on the *result*:
   PT_INTERP, DT_NEEDED, GLIBC requirements, ABI note, SDL
   SONAME and any transitive dependencies. No foreign ldd.
   Ensure no executable DT_NEEDED libEGL/libGLESv2 unless
   independently justified. Runtime EGL/GLES/ION/pixmap closure
   and physical presentation remain UNKNOWN and NOT_TESTED.
7. Adapt only offline mock tests for the alternative variant to
   assert all function lookups, null-pointer failure branches,
   real draw/swap calls, bounded output and clean shutdown.
   Be explicit: host mocks/static link are NOT H700 graphics
   evidence, and success must never be inferred from missing
   real hardware/driver input. Do not replace PR #23 tests.
   Do not create a distributable Pak.

PHASE C — SOURCE REVIEW AND DELIVERY
8. Update only Issue-26-scoped docs/JSON/scripts in EXISTING
   PR #27. Record full pinned source/hash/link evidence, which
   variant was compiled, M4 resolution or failure, link closure,
   and remaining exact vendor/runtime/rights unknowns.
   Distinguish M4_NATIVE_FIXED, GLIBC49_HOST_BUILT,
   SDL_SOURCE_BUILT, SDL_ONLY_HOST_LINKED,
   H700_RUNTIME_NOT_TESTED, and DISTRIBUTION_BLOCKED.
9. CI must remain read-only/offline, test the complete
   branch-vs-base PR diff and never fetch/bundle toolchain,
   SDL binaries, driver blobs, or execute an ARM target.
   Re-run both offline suites, check CI and document exact
   head SHA/runs; do not claim CI rebuilt glibc/SDL.
10. No SSH commands, firmware/library installs, GPU device
    access or other action on the RG35XX Pro. No merge/close
    PRs or Issues; do not begin engine compilation or games.
    Honor license gate PR #19; no combined-work release
    clearance is implied by source build or SDL-only linking.

If the new M4 build works but SDL still needs genuine unavailable
vendor inputs, stop with the exact evidence rather than faking
a solution. If SDL-only linking works, that is SOURCE/HOST
feasibility only; owner hardware GPU-test remains separate.
```

## Erwarteter Abschluss

Codex soll **denselben PR #27** aktualisieren, ohne PRs #19–#25 anzufassen. Das Ziel ist ein nachprüfbarer, möglichst vendor-unabhängiger **Link-Zeit**-Nachweis für ein spiel­freies GLES2-Programm. Die echten Mali-/EGL-/GLES-Treiber und Rechte bleiben eigene Freigabeschritte.

**Kein Geräte- oder Binärtest ist mit diesem Auftrag autorisiert.**
