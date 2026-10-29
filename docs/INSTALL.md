# Install, use and recover the private RMXP Pak

**Not a public release.** Tested layout: RG35XX Pro, BaseOS 1.4.0,
NextUI-20261013-0 (`39a06de`), Linux 4.9.170 aarch64. Knight Blade is the
owner-tested game, not proof of Infinite Fusion/Decay or other firmware support.
There is no approved downloadable engine zip. This guide uses an already
reviewed **private** runtime; it does not authorize redistribution or tagging.

## 1. Before changing the card

- Quit the game and shut down/eject safely. Back up existing saves to a computer.
- Use a preparation computer with Python **3.11+**; the H700 needs no Python.
- Obtain your games and any required RTP/font/soundfont legally. Do not upload
  them, snapshots, raw logs or runtime binaries to GitHub.
- Have the reviewed private runtime directory (`engine`, `LICENSE.txt`,
  `stdlib/`). The installer expects engine SHA-256
  `33b15913859596645d4051bed403e6f0e0953e6d8366db3b06665a9a96ce73f3`.
  Do not disable the hash check to use an unrelated engine.
- Mount the SD card normally. In the commands below replace `/media/CARD` and
  `/private/runtime` with actual preparation-computer paths, not H700 paths.
  Take care to select the card's root, not your system disk.

## 2. Install once, register each game

Run from the source repository. This writes only the card's new Pak directory
and refuses an existing Pak instead of overwriting it:

```sh
python3 scripts/rmxp_pak.py install \
  --sd-root /media/CARD --runtime /private/runtime \
  --pause-menu rgss/pause_menu.rb
```

Optional: also pass `--session /private/rmxp-session.aarch64` for the reviewed
native process supervisor. Only its documented hash is accepted. Without that
helper, use the game's Shutdown action or the pause menu's Quit; the hold chord
is unavailable.

Put an owner's game in `Games/Knight Blade/` on the card. It needs `Game.ini`
and `Data/`, `Graphics/`, `Audio/` directly inside that folder. Register it:

```sh
python3 scripts/rmxp_pak.py register \
  --sd-root /media/CARD --game '/media/CARD/Games/Knight Blade' \
  --name 'Knight Blade'
```

Registration makes a full private working copy and a small `.rmxp` entry.
Allow enough free space for that extra game copy plus backups. Names may include
spaces/Unicode; quote shell paths. Source directories containing symlinks are
refused. Re-running registration never replaces existing saves. For customised
scene scripts/Essentials, use `--no-pause-menu` until a game adapter is tested.
Installing a pause script later does not change existing registrations.

For Knight Blade's external media, privately supply:

```text
CARD/Bios/RMXP/Standard/Graphics/...
CARD/Bios/RMXP/Standard/Audio/...
CARD/Bios/RMXP/TimGM6mb.sf2
```

Retain the soundfont's notices. A game may need a different licensed font or
RTP configuration; a Windows DLL is not a native H700 dependency replacement.

## 3. On the device

Safely eject/reinsert, start NextUI, open **RPG Maker XP**, select the game's
entry. Do not run the graphical launcher concurrently over SSH while NextUI or
another game owns the display. Source `.rmxp` markers are launch entries, not
ROMs; don't rename or move their source folder after registration.

- Confirm: physical A. Cancel: physical B. Start: the game's menu.
- With the pause script: **Menu** opens Continue/Save/Load/Quit; B or Menu closes.
  Save/Load use the game's normal slots and are grey during events/dialogues.
- With the supervisor and verified `session.conf`: hold Select+Start 1.5 s to
  quit. Prefer saving first; forced termination during writes may corrupt a save.
- No emulator save states, instant resume, game switcher or built-in MinArch
  menu. The optional overlay is original RGSS code, not MinArch integration.

On the tested firmware, `ANBERNIC-keys` was `/dev/input/event1`: Select=310,
Start=311, Menu=312, L1/R1=308/309, L2/R2=314/315. Don't guess codes after a
firmware change. The optional per-game `session.conf` beside `mkxp.json` has
exactly three newline-terminated lines: event path, 310, 311. It is data, never
shell code. See [session details](RMXP_SESSION.md) and [overlay](RMXP_PAUSE_MENU.md).

## 4. Where saves and settings live

| Card path | Contents |
| --- | --- |
| `Emus/h700/RMXP.pak/` | Shared runtime, launcher, optional helper/script |
| `Roms/RPG Maker XP (RMXP)/*.rmxp` | Markers selecting stable per-game IDs |
| `Games/<game>/` | Original owner-supplied input (launcher does not write saves here) |
| `.userdata/h700/nextui-mkxp/<ID>/game/` | Private game copy and game-written saves |
| `.userdata/h700/nextui-mkxp/<ID>/mkxp.json` | Per-game configuration |
| `.userdata/h700/nextui-mkxp/<ID>/data/` | Private controller mapping/engine preferences |

Your new saves will not appear in the original game folder or standard NextUI
emulator save directory. Back up the **entire ID directory**, not just the ROM
marker. IDs are derived from the original relative game path, not its label.

## 5. Backup, upgrade, rollback, uninstall

With the game stopped and the card mounted on the computer:

```sh
python3 scripts/rmxp_state.py snapshot \
  --state /media/CARD/.userdata/h700/nextui-mkxp/ACTUAL_ID \
  --output /private/fresh-backup
python3 scripts/rmxp_state.py verify --backup /private/fresh-backup
```

Backups contain private game assets/saves. Restore is deliberately allowed only
to a **fresh destination**, never over an existing ID. See [state tools](RMXP_STATE.md)
for recovery and [release instructions](RELEASE.md) for the archive checks.

- **Upgrade:** quit, back up, move only the old `Emus/h700/RMXP.pak` into
  `RMXP-rollback/<old-version>/` outside `Emus/`. Install the reviewed replacement.
  Never replace `.userdata`, `.system`, games or markers. Preserve optional
  helper/menu support required by per-game configs.
- **Rollback:** retain the new Pak separately, move the old Pak back. A save
  written by a newer engine may need a pre-upgrade backup for an older engine.
- **Uninstall:** move only `Emus/h700/RMXP.pak` off the card. Saves, original
  games and markers remain. Remove those separately only after verifying a backup.

## Troubleshooting (no system modifications)

| Symptom | Safe next check |
| --- | --- |
| No RPG Maker XP entry | Check the exact `Roms/RPG Maker XP (RMXP)/` folder and registered `.rmxp` marker |
| `Game.ini missing` | Check both original and private game roots; don't delete saves to repair it |
| Returns immediately, even with exit 0 | Read private `run.log`; old launchers omitted `SRCDIR` and ignored `mkxp.json`. Use the reviewed launcher |
| Missing library / loader error | Compare pinned hashes and [ABI report](H700_ENGINE_ABI.md). Never replace system libc/GPU libraries |
| Black screen / GLES failure | Stop; collect bounded logs and firmware. Restore the known Pak; no driver/kernel tweaks or forced power cut |
| No MIDI / missing font | Check private RTP/soundfont/config and game font requirements. Do not distribute proprietary fonts |
| Menu opens on L2 | Wrong Menu code: 314 is L2 on the tested firmware; Menu is 312 |
| Chord does nothing | Verify helper, per-game config and actual event/keycodes; release both buttons before trying |
| Game busy / lock exists | Check that the game/process really stopped. Do not remove a lock or partial restore automatically |
| Missing save | Look in the per-ID private game copy; confirm the selected instance and stable source path |
| Slow start / memory pressure | Record game/version, load time and memory; don't assume an OOM from a slow load or enable zram/sysctl changes |

Share only a diagnostic export, not raw logs (which may contain private paths):

```sh
python3 scripts/rmxp_state.py diagnostics \
  --state /media/CARD/.userdata/h700/nextui-mkxp/ACTUAL_ID
```

## Evidence and release boundary

Install/launch, saves, shutdown, source preservation, Pak replacement and reboot
were owner-tested on the firmware above; see [batch results](RMXP_BATCH_TEST.md).
Menu behaviour is [owner-confirmed](RMXP_PAUSE_MENU.md). This newly written guide
has not yet had an independent beginner walk-through, so #17 stays open.

Before public release, require [license/source/relink sign-off](DISTRIBUTION_GATE.md),
an exact versioned candidate with all checksums, the R1–R7 hardware checklist and
both target-game compatibility reports or an explicitly reviewed limited beta.
No tag, release or binary download is created by this documentation. Knight
Blade's private playability remains **100%**; public release is a separate gate.
