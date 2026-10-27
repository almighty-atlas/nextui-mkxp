# Acceptance and regression test plan

## Evidence levels

- **STATIC:** docs, shell syntax, archive structure and deterministic scripts.
- **HOST:** host/cross-toolchain build, ELF readelf output and linker/SONAME scans.
- **H700:** actual RG35XX Pro running a documented NextUI version, with sanitized logs.
- **OTHER DEVICE:** ArkOS/R36S reports, for context only, **never** substitute for H700.

## M1: Engine

- Pinned reproducible input revisions; failed network/downloads are explicit.
- `file` and `readelf -h/-l/-d` confirm correct ABI/interpreter/NEEDED libraries.
- No foreign ARM32 libraries bundled accidentally; no direct private-path dependencies.
- SDL video opens on physical screen, draws known visual output and exits.
- Audio device opens/plays test tone only where permitted; verify silence-on-exit.
- Controller input (d-pad, A/B, START/SELECT, MENU) mapped on hardware.

## M2: Pak

- Detects missing `Game.ini`/missing data with actionable message; no partial state damage.
- ROM path with spaces / Unicode; multiple games, isolated saves and config.
- Menu/exiting returns to NextUI; process tree clean; no accidental key capture.
- Forced quit (where safe), restart and power-interruption recovery are explicitly tested.
- Logs default to bounded and privacy-safe; debug mode opt-in and removable.
- Install/uninstall does not write into `.system` or alter existing Paks.

## M3/M4: Each target game

- Record release/hash, startup time and title/menu.
- Create/load a save, use controls, talk to NPCs, enter/exit buildings and menus.
- Run trainer/wild battle, audio cues, effects, dialogs, fade transitions.
- Infinite Fusion: fusion/unfusion and custom sprites under realistic memory pressure.
- Decay: scripted events, scripted battles and installed Essentials extensions.
- Repeat cold boot 3 times and play an extended session with memory/FPS/thermal sampling; record failures and crash signal.
- Document specific scenes where slowdown happens rather than a single average FPS.

## Test result template

| Test | Evidence level | Device/firmware | Result | Evidence file / command |
| --- | --- | --- | --- | --- |
| Example | H700 | RG35XX Pro / exact NextUI tag | NOT_TESTED | — |

Use PASS / FAIL / BLOCKED / NOT_TESTED. Never claim PASS without corresponding actual execution.

## Recorded narrow video result and next host gate

[Issue #22 / PR #30 evidence](H700_VIDEO_EVIDENCE.md) records one owner-run H700
video PASS separately from supplied host build facts and physical observation.
Do not promote this to M1 engine/audio/input acceptance. Exact NextUI release,
orientation and process audit remain incomplete; a log's cleanup/exit code alone
does not establish a responsive UI. No further hardware test is requested now.

The [next implementation milestone](H700_MINIMAL_ENGINE_PLAN.md) defines offline
lockfile/cache rejection tests, C++ ABI calibration and engine-stage acceptance.
Current offline regression commands (no ARM execution):

```sh
python3 -I -B -m unittest discover -s spikes/h700-stock-video -p 'test_*.py' -v
```

This includes evidence-consistency checks and existing synthetic ELF/assembly
tests. It does not inspect the tested private ELF or repeat the owner's trial.
