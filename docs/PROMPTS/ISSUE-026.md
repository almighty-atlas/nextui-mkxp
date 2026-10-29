# Codex-Master-Prompt — Issue #26: Linux-4.9-Sysroot und H700-Mali-Linkage

**Projekt:** [almighty-atlas/nextui-mkxp](https://github.com/almighty-atlas/nextui-mkxp)<br>
**Aufgabe:** [Issue #26](https://github.com/almighty-atlas/nextui-mkxp/issues/26)<br>
**Zulässige Arbeit:** isolierte Quellen-, Host-Build- und ELF-Prüfung. **Keine Ausführung, Installation oder Änderung auf dem Handheld.**

## Codex-Auftrag

```text
Repository: almighty-atlas/nextui-mkxp
Implement only Issue #26:
[M0 SPIKE] Retarget AArch64 libc/sysroot for Linux 4.9 and H700 Mali linkage.

Your target is a concrete, auditably built AArch64 artifact (private host
workspace ONLY), preferably with a GNU Linux ABI note <= 4.9 and actual
H700-compatible SDL/GLES linking. If either cannot be established, stop at
the first reproducible blocker rather than claiming target compatibility.

REVIEW BEFORE WORK:
- AGENTS.md, docs/ROADMAP.md, docs/SOURCES.md, linked roadmap Issue #18;
  Issues #1, #2, #3, #4, #22, #24 and new Issue #26.
- Open PRs #19–#25, especially #21's ADR, #23's original triangle.c and
  source-only launch.sh, and #25's full doc/lock/build-gate/crosscheck/tests.
- Read review comments on PR #25; keep them as mandatory input.
- Use source SHA 8a08fe77d8675eb93368c15bd5fd3ddc1b00d9dd9229b8eda595e0a0e1432c42
  for the original triangle and PR #23 head
  60721c1a81a9f54e507650f313a479ecaa9b6d2a.
- Source pins in PR #25 are the baseline; check upstream revisions explicitly.
  No PR #19–#25 is merged; don't edit/rebase their branches. Start fresh
  from origin/main, use standalone new docs/build/issue-26-* and
  scripts/issue_26_* paths (unless a separately documented conflict-free
  approach is better), avoiding overlaps with PR #25.

PHASE A: ROOT-CAUSE AND RETARGETING
1. Independently verify why the GCC 8.3/glibc 2.28 sysroot in PR #25
   encodes GNU/Linux ABI note 4.19: read *pinned* CT config,
   Linux headers, glibc crt1.o/startup objects and actual readelf evidence.
   Both x86_64-host and aarch64-host toolchain configurations declare
   CT_GLIBC_MIN_KERNEL="4.19"; switching compiler host architecture
   is not a fix.
2. Research the real constraints of glibc 2.28 and crosstool-NG 1.25
   when configured for a minimum Linux 4.9 kernel. The 4.19 ABI
   note is a static gate, not a proven H700 execution failure.
   Determine if Linux 4.9-compatible kernel headers + glibc startup
   objects can be built in an isolated sandbox. Do not assume that
   merely patching a config, swapping crt1.o from unrelated libc,
   editing ELF .note.ABI-tag or force-linking is safe.
3. Evaluate candidates in order:
   (a) source-pinned rebuilt glibc/sysroot + known compiler with
       compiler/runtime consistency;
   (b) existing pinned AArch64 Linux toolchain with appropriate
       glibc/kernel baseline, if its compatibility and provenance
       can genuinely be verified;
   (c) a documented blocked option if no safe, licensed inputs exist.
   Check that a lower ABI note does not hide unsupported syscalls or
   versioned symbols. No alteration of the device kernel or firmware.
4. If resources and rights allow, perform a REAL isolated host build
   of the ORIGINAL PR #23 triangle with the retargeted sysroot.
   Record source commits, exact hashes, flags, interpreter, NEEDED,
   required symbol versions and ABI notes using native readelf.
   Keep every ELF/archive private to temporary host workspace;
   do NOT commit, upload, publish, deploy or run the target binary.
   If a full glibc/toolchain rebuild is too resource-intensive or fails,
   document measured stage/exit reason and the smallest safe next step.

PHASE B: H700 GRAPHICS ABI (SEPARATE GATE)
5. Inspect pinned NextUI H700 "mali" SDL2 and its actual build
   recipe/headers (SDL 2.28.5 in the owner's library filename;
   source identity is not yet attested). Compare symbol APIs/SONAME
   with the original triangle. Distinguish SOURCE_CONFIRMED from
   installed-device bytes, which remain UNKNOWN.
6. The existing PR #25's TrimUI SDK SDL 2.26.1/PowerVR libraries
   permitted a LINK but are *not* H700-Mali runtime evidence.
   Identify a reproducible H700 SDL2/EGL/GLES *link interface*
   using license-reviewed source/headers and authentic link inputs
   if available. If H700 vendor libraries are unavailable, report
   LINK_BLOCKED and request no fictional shim or dummy-success
   library. Do not copy or repackage PowerVR, GPU/vendor, or stock
   system shared libraries. Never hide unresolved symbols or link
   against x86_64 host dependencies.
7. Keep libc minimum-kernel compatibility and Mali linkage as
   INDEPENDENT statuses. A correct ELF header, successful link,
   lowered GNU ABI note or a stub compile alone do not prove
   target runtime compatibility.

PHASE C: HARDENING, TESTS AND DELIVERY
8. Reuse PR #25's pattern but improve build hermeticity:
   don't inherit the entire host environment by default.
   Audit LD_PRELOAD, LD_LIBRARY_PATH, LD_AUDIT, PYTHONPATH,
   LD_DEBUG, GCC_EXEC_PREFIX, COMPILER_PATH, CPATH,
   C_INCLUDE_PATH, CPLUS_INCLUDE_PATH, LIBRARY_PATH,
   PKG_CONFIG_* and tool wrappers, LC_ALL/LANG, PATH, HOME,
   TMPDIR, network-fetchers. Define a minimal documented host
   tool allowlist. Log the provenance of selected binaries and
   searched include/library paths.
9. Add offline negative tests: hostile environment/preload,
   unknown file/link provenance, unexpected host includes,
   mismatched ABI note, GLIBC floor, RPATH and NEEDED, malformed
   input, and unsafe symlinks. CI stays offline, read-only,
   with no target execution or external binary uploads.
10. Keep strict license stop: MIT original triangle does not
    authorize distributing a combined SDL Mali/GPL/vendor work.
    Document which exact source/notice exceptions would be needed.
    Consult PR #19's gate; do not auto-approve any license conflict
    or treat system-library omission as blanket clearance.
11. Produce a clear comparison matrix:
    - TOOLCHAIN kernel baseline: KNOWN / BLOCKED
    - RETARGETED glibc/sysroot: BUILT / BLOCKED
    - AArch64 object compiled: PASS / NOT_TESTED
    - AArch64 link against compatible H700 interface: PASS /
      LINK_BLOCKED
    - ELF/PT_INTERP/DT_NEEDED/GLIBC/ABI-note: PASS_STATIC / BLOCKED
    - H700 installed runtime hashes, /dev/ion, actual video:
      OWNER_NOT_TESTED
    - Distribution/rights: BLOCKED unless separately approved.
    Explicitly label the evidence level SOURCE, HOST or H700.
12. Deliver ONE unmerged PR with commands, inputs, pinned hashes,
    reproducibility limits, test results and next non-device step.
    Report the first reproducible unresolved blocker, if any.
    Do not modify PRs #19–#25, close Issues #22/#24/#26,
    begin the mkxp-z engine build, or give the owner an H700
    command to run. No shared changes to .system, firmware,
    hardware peripherals or NextUI Tools.

The user currently permits source-code/host-build review ONLY.
This task has no device access or deployment authorization.
```

## Erwartetes Ergebnis

Ein belastbarer, möglichst tatsächlich gebauter **Linux-4.9-tauglicher AArch64-Test-Build** in einer privaten Host-Umgebung, inklusive überprüfbarer ELF-Metadaten. Falls die realen H700-Mali-Bibliotheken zum Linken nicht verfügbar sind, muss dieser Punkt ausdrücklich als eigener Blocker stehen bleiben.

Dies ist **keine** Genehmigung, Binärdateien zu veröffentlichen oder auf dem RG35XX Pro auszuführen.
