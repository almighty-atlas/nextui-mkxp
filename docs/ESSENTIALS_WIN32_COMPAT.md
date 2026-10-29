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

## Ruby 1.8 syntax repair

Second owner launch (verified-on-H700): the shim loaded, but both games then
stopped on parse errors. RGSS1 is Ruby 1.8, and the engine runs Ruby 3.1:

| Game | Section:line | Construct |
| --- | --- | --- |
| Sage | 046 AudioUtilities:919 | `when 0:` (colon instead of `then`) |
| Sage | 171 PSystem_Utilities:199, Rocket 190:300 | `\x7f-\x9f` in a regexp (invalid in UTF-8) |
| Sage | 184 SAGE Battle MoveEffects:401 | `x=0.` before `elsif`/`end` |

mkxp-z decodes `$RGSS_SCRIPTS` before running preloads, so the shim rewrites
the decoded text of a section **in memory** before it is evaluated. Game files
are never changed. Three narrow rules exist, one for each construct above. They
keep line numbers, skip sections with invalid UTF-8, and a rewritten section is
kept only if it then compiles. Private host harness: all 209 Sage and 211
Rocket sections compile after the repair. Only the lines listed above change.
Ruby 1.8 behaviour at runtime (as opposed to syntax) is not emulated.

`scripts/enable_rmxp_compat.py` copies the hash-pinned shim into
`.userdata/h700/nextui-mkxp/<id>/compat/` and sets the preload. An earlier
reviewed shim version is upgraded in place. It refuses other
existing preloads (e.g. the Knight Blade pause menu) and never touches the
shared Pak. Knight Blade is unaffected.

## Verification

| Level | Check | Result |
| --- | --- | --- |
| verified-on-host | Synthetic Ruby suite `tests/essentials_win32_compat_test.rb` (Ruby 3.1.3, pinned container) | 11 runs, 0 failures |
| verified-on-host | Private harness (not committed) that loads both games' real Win32API, controls, file and font-installer scripts after the shim | Window found; trigger only on first held frame; repeat from frame 21; release, dir4/dir8, B, A, F5 OK; save folder `.`; registry default; font installer no-op |
| verified-on-host | Synthetic Ruby 1.8 repair cases in the same suite | PASS |
| verified-on-H700 | Shim + updated `mkxp.json` installed for both games, prior `mkxp.json` kept as `mkxp.json.pre-compat` | checksums PASS; existing saves and shared runtime unchanged |
| verified-on-H700 | Second launch with first shim | Win32API error gone; Ruby 1.8 parse errors above |
| verified-on-H700 | Repaired shim `88380c8d…` upgraded in place for both games | checksums PASS; saves and shared runtime unchanged |
| untested | Title screen, audio, controls, new game, save/load on H700 | needs owner launch |

Rollback per game: restore `mkxp.json.pre-compat` over `mkxp.json`, then remove
`compat/`.
