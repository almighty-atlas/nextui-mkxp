# Codex master prompt — Issue #24: H700 AArch64 toolchain and ELF gate

**Repository:** [almighty-atlas/nextui-mkxp](https://github.com/almighty-atlas/nextui-mkxp)  
**Issue:** [#24 — Verify AArch64 toolchain, sysroot and ELF ABI for H700 GLES test](https://github.com/almighty-atlas/nextui-mkxp/issues/24)  
**Existing source:** [PR #23](https://github.com/almighty-atlas/nextui-mkxp/pull/23), source-only GLES2 triangle.  
**H700 graphics runtime:** NOT_TESTED. **Do not use or change the owner's device** for this task.

## Copy the following into Codex

```text
Repository: almighty-atlas/nextui-mkxp
Work ONLY on Issue #24:
[M0 SPIKE] Verify AArch64 toolchain, sysroot and ELF ABI for H700 GLES test.

Goal: make tangible progress toward a correctly built ORIGINAL C triangle
test executable. Do not stop at another architecture essay if an actual
isolated cross-build and ELF analysis are feasible. However, do not
invent missing hashes/licensing, upload an executable or deploy to H700.

BEFORE CHANGES
- Read AGENTS.md, docs/ROADMAP.md, docs/SOURCES.md, Issue #24,
  Issue #22, PR #23 (its full source/test files), Issue #1 inventory,
  PR #21 ADR, and PR #19 provenance STOP/GO gate.
- Inspect PRs #19, #20, #21 and #23 (all unmerged). Do not merge,
  rewrite or modify their branches.
- Make an independent branch from current origin/main. Add new files
  under docs/build/ and/or scripts/ only where practicable. The source
  triangle remains in PR #23; read it from the PR head and use it
  solely in a temporary isolated build checkout. Don't duplicate it
  into your branch or force an unmerged PR dependency into main.

TOOLCHAIN AND INPUT PINNING
1. Inspect pinned LoveRetro/h700-toolchain revision
   04faa348c112617fc6b99be62308099ee6d43581 and its Dockerfile.
   It names aarch64-nextui-linux-gnu GCC 8.3 and a TrimUI SDK sysroot;
   the latter is NOT the same as an attested H700 runtime.
2. The x86_64 compiler archive from
   LoveRetro/gcc-arm-8.3-aarch64-tg5040 release
   v8.3.0-20260204-190602-d37268f5 is named
   gcc-8.3.0-aarch64-nextui-linux-gnu-x86_64-host.tar.xz.
   GitHub publishes its SHA256 as:
   d4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3
   Verify actual downloaded bytes independently before extraction.
   Validate archive paths for traversal/link surprises; do not pipe
   unknown archive content straight to an extractor or install to /opt.
3. The TrimUI 20231018 SDK asset SDK_usr_tg5040_a133p.tgz has
   NO digest in the observed release metadata. If permitted and
   necessary, fetch it to a sandbox, independently hash it and
   record URI/date/bytes/sha256 and license. Do not treat an
   independently computed hash as a pre-existing upstream attestation.
   Inspect archive paths before safe isolated extraction.
4. Pin any container base digest, sources, tools, SDK and build flags.
   Do not use floating :latest as reproducibility evidence; no
   sudo, system package installation, host global changes or device I/O.
   If available sandbox tools do not permit safely verifying/extracting
   an input, name the exact blocker.

ACTUAL TARGET BUILD AND ABI CHECK
5. Determine whether the pinned SDK genuinely supplies SDL2, GLES2,
   EGL headers+link stubs needed for the original triangle.c from
   PR #23. Avoid falling back to x86 host includes/libraries. The
   proposed H700 SDL is a Mali-fbdev patched fork; distinguish actual
   installed runtime from generic TrimUI headers/stubs.
6. If legally permissible and feasible, compile triangle.c for
   aarch64-nextui-linux-gnu in the ISOLATED workspace, without
   executing it or creating a distributable zip. Log exact
   compiler --version, -dumpmachine, include/library resolution,
   input revisions, command, exit code and output SHA256.
   On failure, classify the FIRST reproducible error and propose the
   narrowest fix without replacing device runtime/driver libs.
7. Use host file/readelf, not foreign ldd, to capture ELF class,
   machine, endian, PT_INTERP, DT_NEEDED, RUNPATH/RPATH, symbol
   version requirements (GLIBC_* / GLIBCXX_* if applicable), and
   link map. Explicitly record dlopen-relevant GLES/SDL/vendor
   dependencies that ELF NEEDED alone cannot enumerate. Fail closed
   on unexpected host dependencies.
8. Compare against owner-observed /bin/sh AArch64 and known file
   presence ONLY. Exact installed H700 SDL/libc/loader hashes,
   /dev/ion availability, installed symbol version floor and GLES
   initialization remain UNKNOWN until separately observed.
   Never label the built artifact verified-on-H700 just because
   an AArch64 executable links on a host.

RIGHTS, DELIVERY AND SAFETY
9. Resolve the narrowly scoped question: what notices/source would
   be needed to DISTRIBUTE this original triangle app dynamically
   linked to installed H700 SDL2/EGL/GLES? The fork contains
   GPL-noticed mali.h; MIT licensing of triangle.c is not
   a blanket license for the combined linked work. List uncertain
   terms and necessary human decisions. Do not silently decide
   legal compatibility or lift PR #19's STOP gate.
10. Commit ONLY new reproducible scripts, tests, lockfile and
    documentation. Do not commit/upload executable binaries,
    toolchain archives, SDK blobs, runtime .so, proprietary fonts
    or ROM/game content; no GitHub release artifacts.
11. If necessary, prepare ONE consolidated, read-only *future*
    SSH inventory script or exact safe host-side file inspection
    plan to collect /dev/ion type/access, selected installed
    SDL/EGL/GLES/libc/loader hashes and ELF versions, without
    opening the graphics display or disclosing passwords/IP/MAC,
    dumping all environment or changing anything. DO NOT execute
    it on the user's device or require them to do so now.
12. Add deterministic offline/static tests (hash-format checks,
    pinned source refs, ELF scanner fixture and correct failure
    handling) that don't depend on network in CI. Never run the
    graphical executable under SSH/CI/emulator as if it were H700.

PR DELIVERY
- Open one unmerged PR referencing Issue #24; link PR #23 but do
  not close/merge/update PRs #19-#23.
- Report SOURCE_CONFIRMED / HOST_VERIFIED / OWNER_OBSERVED_H700 /
  H700_RUNTIME_NOT_TESTED / BLOCKED separately.
- Include pinned downloads and ACTUAL hashes/commands, first
  failed build stage, if any, new test cases, notices/source gate,
  the smallest next action, and exact conflicts/dependencies.
- Do not initiate Issue #4's full engine build or any Pokemon test.
```

## Desired outcome

A real target-ABI cross-compile attempt and independently inspectable ELF evidence if safe inputs are available. Otherwise an exact list of missing toolchain/header/license/runtime facts and a **single read-only future inventory handoff**. Source-code review remains the only user action now.

**The next device action is not authorized by this prompt.** Hardware graphics stays `NOT_TESTED` until a separately reviewed build and on-screen NextUI Tools run.
