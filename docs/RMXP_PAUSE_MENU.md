# In-game pause menu on the Menu button (#45)

Status: **verified-on-H700** with Knight Blade (RG35XX Pro, NextUI-20261013-0,
2026-10-29), plus host tests. Original MIT-licensed code; no game scripts copied.

`rgss/pause_menu.rb` is an mkxp-z `preloadScript` for RGSS1 (RPG Maker XP)
games. The Menu button opens an overlay similar to MinArch's in-game menu:

| Item | Behaviour |
| --- | --- |
| Continue | Close the overlay (also Menu or B). Paused time is not added to play time |
| Save | The game's own save screen via `$game_temp.save_calling`, as the "Call Save Screen" event command does. Returns to the map |
| Load | The game's own load screen. Cancel returns to the map instead of the title screen |
| Quit | Asks for confirmation ("Cancel" preselected), fades audio, then ends through the default `Main` loop (`$scene = nil`) so mkxp-z exits normally and NextUI returns |

Save and Load are greyed out unless the player is on the map with no event or
message running. Save also respects the game's "save disabled" flag. Load needs at
least one `Save1`–`Save4.rxdata`. Continue and Quit are always available.

These are **not** emulator save states: RGSS/Ruby state cannot be snapshotted,
so Save writes the game's normal save slots. There is no NextUI game switcher,
instant resume or Options/volume item.

## Input

The Menu button is read passively from evdev, like the [#10 chord](https://github.com/almighty-atlas/nextui-mkxp/pull/42).
The device is found by name (`ANBERNIC-keys`) in `/proc/bus/input/devices`,
opened read-only and non-blocking, never grabbed or written. Observed codes on
`event1`:

| Button | Code |
| --- | --- |
| Menu | 312 (then 354 on release) |
| L1 / R1 | 308 / 309 |
| L2 / R2 | 314 / 315 |
| Select / Start | 310 / 311 |

A first attempt used 314 and opened on L2. The second passive capture
corrected this. Menu navigation uses the game's normal RGSS input (D-pad,
confirm, cancel). After closing, the overlay waits until confirm/cancel are
released so the press does not reach the game. If the device is missing or
disconnected, or the overlay raises an error, the menu disables itself
(`NEXTUI_PAUSE_ERROR=<class>` in `run.log`) and the game keeps running.

## Enabling for a game

Place the script outside the engine bundle and add it to that game's
`mkxp.json` after backing the file up:

```json
"preloadScript": ["/mnt/SDCARD/.userdata/h700/nextui-mkxp/<ID>/pause_menu.rb"]
```

Automatic installation by the #40 registration tool is a follow-up. Only
enable it for games using the standard RMXP scene classes (`Scene_Map`,
`Scene_Save`/`Scene_Load` < `Scene_File`, `Game_Temp#save_calling`). Heavily
customised games and Pokémon Essentials need a separate adapter. Scripts that
replace `Input.update` without calling the original disable the overlay.

## Verification

- Host: `ruby tests/pause_menu_test.rb` (or `RMXP_RUBY=/path/to/ruby python3 -m
  unittest discover -s tests`). 13 tests, 45 assertions PASS with Ruby 3.1.3
  built from the existing pinned release tarball (SHA-256
  `4ee161939826bcdfdafa757cf8e293a7f14e357f62be7144f040335cc8c7371a`) in a
  network-disabled, unprivileged container. They use synthetic RGSS stand-ins
  and real evdev byte records over a pipe. They cover device lookup,
  pass-through, autorepeat/other events, Continue/Menu/B close, play-time
  restore, Save, Load with cancel-to-map and `$game_temp` restore, disabled
  states, Quit confirmation, held-button release, error isolation and disconnect.
- Knight Blade's scripts were checked for the standard scene classes and
  methods (names only, no content copied).
- H700 (owner observation): Menu opens the overlay and closes it again, L2 no
  longer opens it, and Continue, Save, Load and Quit all work. Quit returned
  to NextUI with `RMXP_EXIT=0`.
