# Codex task — GitHub Issue #1 (H700 hardware baseline)

## Goal

Prepare a **safe, minimally intrusive, reproducible hardware/NextUI inventory** for the actual Anbernic RG35XX Pro (H700), so the mkxp-z build and standalone Pak integration can be based on observed facts rather than the R36S/ArkOS assumptions.

**This task has an unavoidable hardware handoff.** Codex can write and statically test a read-only probe; it must **not** claim the physical device was tested until the user provides redacted device output.

## Instructions for Codex

```text
Repository: almighty-atlas/nextui-mkxp
GitHub Issue: #1 — [M0] Inventory RG35XX Pro / NextUI H700 hardware,
ABI and Pak runtime.

Read AGENTS.md, README.md, docs/ROADMAP.md, docs/ARCHITECTURE.md,
docs/DEVICE_PROBE.md, docs/TEST_PLAN.md, docs/SOURCES.md, Issue #1 and
any active PRs before editing. PR #19 contains a separate, unmerged
license audit: do not change that branch or duplicate its files.

On a fresh branch from origin/main, make a narrowly scoped change:

1. Confirm the read-only probe uses BusyBox-compatible shell syntax
   and succeeds gracefully when /bin/sh commands or /proc nodes
   are missing. Test syntax with sh -n and use shellcheck if available.
2. Provide ONE directly executable, non-privileged diagnostic script
   (for example tools/probe-h700.sh) emitting human-readable sections:
     - exact device/NextUI release if reliably available
     - uname architecture vs 32/64-bit userland and executable ABI
     - loader/libc and available relevant SDL2/EGL/GLES/DRM/audio libs
     - memory/swap, safe device-node presence and access bits
     - controller/input devices without reading private event streams
     - NextUI/Pak directories, runner variables limited to documented
       non-sensitive names (do not dump all environment variables)
   Avoid overclaiming: presence of a device node or shared library
   does NOT prove functional GLES, audio, controller or display.
3. Add sanitized sample-output or fixture tests; verify the probe
   cannot silently run sudo, modify system configuration, install
   packages, mount filesystems, open arbitrary user files or alter
   firmware. No network discovery, MAC/IP/SSID/token output.
4. Document exactly how to run the script from an existing terminal
   or SSH session **only if already available**. Do not assume SSH
   connectivity or make changes to enable SSH.
5. If the inventory cannot safely infer a required property, mark
   UNKNOWN and give the smallest next non-destructive verification
   step instead of inventing values.
6. Update docs/DEVICE_PROBE.md and (where truly needed) architecture
   assumptions. Keep all hardware results explicitly NOT_TESTED
   until the user has actually run the tool on their RG35XX Pro.

Do not compile mkxp-z; do not start cross-build issue #4, import R36S
patches, bundle any game files, write to .system, flash a card,
alter zram/sysctl/governor, install packages or require sudo.

Open a PR referencing #1. Do not merge or close #1. Include:
- exact commands and actual static/host checks;
- inventory field rationale and redaction rules;
- evidence-level table (STATIC/HOST/H700);
- a single copy/paste command for the user to run manually;
- which issue acceptance criteria remain blocked on real H700 output.
```

## Acceptance handoff

1. Review the PR for strict read-only behavior.
2. User runs the reviewed command once on their RG35XX Pro.
3. Append **redacted** output and installed firmware version to Issue #1.
4. Codex uses that evidence to finalize the M0 ABI/Pak baseline. It must not label H700 as verified before step 3.

No game assets, secret files, binary distributions or destructive changes.
