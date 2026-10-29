# Essentials Win32API compatibility shim (#52)

## Observed failure (verified-on-H700)

First owner launch of Pokemon Sage and Pokemon Team Rocket on 2026-10-29
(NextUI-20261013-0, engine `33b15913…`). Both stopped before the title screen
with the same error in their `run.log`:

```
004:Win32API:3:in `initialize': wrong number of arguments (given 4, expected 0) (ArgumentError)
```

The H700 engine is built with `use_miniffi: false`
([profile](../build/h700-engine/mkxp-z-profile.json)), so no `Win32API`
class exists. Essentials 17.2's script 4 reopens `Win32API` and creates
handles in its class body. Simply enabling MiniFFI would not help: the games
load `user32`/`kernel32` and similar Windows libraries, which do not exist on Linux.

## Adapter

[`rgss/essentials_win32_compat.rb`](../rgss/essentials_win32_compat.rb) (MIT,
original) is enabled **per game** as its only `preloadScript`. It:

- defines `Win32API.new(dll, function, ...)`. Every call answers like an
  unavailable API: 0, `ERROR_FILE_NOT_FOUND` for the registry, `E_FAIL` for
  shell folders, an MCI error. Loading native code is never attempted;
- reports a consistent window/thread identity, so `pbFindRgssWindow` and
  `pbSameThread` succeed, and fills window rectangles with the game resolution;
- answers `GetAsyncKeyState` from the engine's **own** RGSS button state.
  Essentials replaces `Input` with Windows key polling, so this keeps the
  reviewed gamepad bindings. Exactly one virtual key per button
  (Enter=C, Esc=B, Z=A, PageUp/PageDown=L/R, F5=F5 or RGSS X), because
  Essentials polls its key aliases lazily. Several "pressed" aliases would
  re-trigger one press on later frames (found by the private harness below);
- turns `FontInstaller.install` into a no-op once the game defines it.
  mkxp-z registers the game's `Fonts/` itself, and the Windows font-folder
  copy could only fail with a prompt on every start.

Consequences visible to the player: no Flash intro in Sage (skipped as "not
playing"), no GIF conversion, no screenshot DLL, no CD/MCI/wave recording, no
online/socket features. Saves resolve to `./Game.rxdata` in the game's private
copy, because the known-folder lookup fails.

`scripts/enable_rmxp_compat.py` copies the hash-pinned shim into
`.userdata/h700/nextui-mkxp/<id>/compat/` and sets the preload. It refuses
existing preloads (e.g. the Knight Blade pause menu) and never touches the
shared Pak. Knight Blade is unaffected.

## Verification

| Level | Check | Result |
| --- | --- | --- |
| verified-on-host | Synthetic Ruby suite `tests/essentials_win32_compat_test.rb` (Ruby 3.1.3, pinned container) | 9 runs, 0 failures |
| verified-on-host | Private harness (not committed) that loads both games' real Win32API, controls, file and font-installer scripts after the shim | Window found; trigger only on first held frame; repeat from frame 21; release, dir4/dir8, B, A, F5 OK; save folder `.`; registry default; font installer no-op |
| verified-on-H700 | Shim + updated `mkxp.json` installed for both games, prior `mkxp.json` kept as `mkxp.json.pre-compat` | checksums PASS; existing saves and shared runtime unchanged |
| untested | Title screen, audio, controls, new game, save/load on H700 | needs owner launch |

Rollback per game: restore `mkxp.json.pre-compat` over `mkxp.json`, then remove
`compat/`.
