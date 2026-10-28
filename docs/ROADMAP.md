# Milestones and issue breakdown

## Active first-game target: Knight Blade — 98%

The [maintained Knight Blade checklist](KNIGHT_BLADE_ROADMAP.md) defines
weighted progress and the 100% acceptance gate. Continue its first unfinished
milestone autonomously, update progress/evidence together, and report missing
access, legally supplied game/RTP files or required human device observations.
This private playability target precedes Pokémon testing; public release remains
a separate gate.

This is a **planning roadmap**, not a statement of implemented features. Phase codes in issue titles are used because GitHub Milestones may not yet be configured.

## M0 — Foundations (prerequisite for engineering work)

- Confirm H700 NextUI aarch64 ABI, graphics, audio, input, memory and exact firmware baseline.
- Compare native mkxp-z, R36S ArkOS port and NextUI Pak lifecycle; write the architecture decision.
- Run a narrowly scoped, independently reviewed, game-free Mali-fbdev GLES2 feasibility spike ([#22](https://github.com/almighty-atlas/nextui-mkxp/issues/22)) **before treating H700 graphics as functional**; this is not the later full engine/audio/input test.
- Verify a pinned cross-toolchain, safe sysroot, ELF ABI and narrow linked-library distribution gate ([#24](https://github.com/almighty-atlas/nextui-mkxp/issues/24)) before any H700 executable is provided.
- Resolve the Linux 4.9 minimum-kernel/sysroot discrepancy and H700 Mali-fbdev link-interface separately ([#26](https://github.com/almighty-atlas/nextui-mkxp/issues/26)); do not equate the prior TrimUI/PowerVR host link with H700 readiness.
- Audit upstream license obligations and dependency provenance before copying code/binaries.
- Establish repository hygiene, offline docs/packaging validations and a safe cross-build environment.

**Exit gate:** evidence-based architecture and development toolchain plan, with a non-privileged read-only hardware report.

## M1 — Native engine

Private Ruby prerequisite progress: [offline extension batch and grouped H700
PASS](H700_RUBY_BATCH.md), 2026-10-28. The first private engine compile/link
also [passes on host](MKXP_Z_SOURCE_LOCK.md), as does the
[static provider ABI audit and H700 loader check](H700_ENGINE_ABI.md).
The first [engine/Ruby and visible rendering test](H700_ENGINE_SMOKE.md) also
passes on H700; audible sound, full controls and public reproducibility remain open.

- Build and package pinned mkxp-z sources and dependencies for real H700 ABI.
- Inspect interpreter/ELF requirements, `NEEDED` libraries, glibc and OpenGL/GLES requirements.
- Minimal game-free engine smoke test, with defined outcomes and logs.
- If video/audio cannot initialize, isolate backend failure before building a full Pak.

**Exit gate:** reproducible build and H700 hardware engine smoke test (or an explicitly documented blocker).

## M2 — NextUI standalone Pak

- Implement layout and valid launch entry point compatible with NextUI's Pak and ROM discovery conventions.
- Game-per-directory discovery with paths containing spaces; absence and error handling.
- Map handheld input, maintain usable exit chord and handle audio/display cleanup.
- Per-game saves/settings and actionable diagnostics without leaking personal paths.
- Safe packaging and manual install/uninstall that leaves NextUI system files untouched.

**Exit gate:** on-device Pak launches a legal test project, exits cleanly and retains saves.

## M3 — Pokémon Infinite Fusion

- Audit supported tested game version and private game content layout (never commit the game).
- Test boots/title screen/field movement/battles/saving/fusions/custom sprites.
- Measure FPS, RAM, load time, zram need, crashes, thermal behavior across repeated cold starts.
- Change settings or add optional memory mitigation only when evidence justifies them.

**Exit gate:** repeatable gameplay checklist with actual RG35XX Pro evidence.

## M4 — Pokémon Decay

- Establish exact game version, engine, Essentials version and platform requirements from developer files.
- Test boot, input, text, audio, saving, scripted battles/events and regressions.
- Fix general engine limitations upstream-first, isolate game-specific workarounds.
- Record limitations even if game is not fully playable.

**Exit gate:** compatibility entry with versioned reproducible results.

## M5 — Release and support

- Reproducible minimal distribution with checksums, license notices and corresponding source.
- Automated archive structure/static validation plus hands-on H700 acceptance tests.
- Install, upgrade, uninstall, troubleshooting and known limitations guide.
- Publish only when distribution obligations and basic safety criteria are met.

**Exit gate:** signed-off release candidate; no game content in archives.
