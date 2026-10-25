# Milestones and issue breakdown

This is a **planning roadmap**, not a statement of implemented features. Phase codes in issue titles are used because GitHub Milestones may not yet be configured.

## M0 — Foundations (prerequisite for engineering work)

- Confirm H700 NextUI aarch64 ABI, graphics, audio, input, memory and exact firmware baseline.
- Compare native mkxp-z, R36S ArkOS port and NextUI Pak lifecycle; write the architecture decision.
- Audit upstream license obligations and dependency provenance before copying code/binaries.
- Establish repository hygiene, offline docs/packaging validations and a safe cross-build environment.

**Exit gate:** evidence-based architecture and development toolchain plan, with a non-privileged read-only hardware report.

## M1 — Native engine

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
