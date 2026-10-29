# RMXP Pak: private integration candidate (#8)

Status: source implementation; hardware discovery and engine launch **NOT_TESTED**.
The separate Knight Blade private boot milestone reached **100%** in
[PR #39](https://github.com/almighty-atlas/nextui-mkxp/pull/39). That evidence does
not verify this new launcher. No engine, game, RTP or soundfont is distributed.

## Discovery contract

Reviewed NextUI revision: `39a06deadfdd2bd08209208ff40752c8e51a449d`.
Sources: upstream `PAKS.md`, `workspace/all/nextui/nextui.c` (`addEntries`,
`hasRoms`, `openRom`, `openDirectory`) and `workspace/all/common/utils.c`
(`hide`, `getEmuName`, `getEmuPath`). These are upstream-source findings, not
on-device verification of this Pak. No upstream implementation was copied.

- `Emus/h700/RMXP.pak/launch.sh` receives one ROM path argument.
- Ordinary files in `Roms/RPG Maker XP (RMXP)/` become ROM entries, regardless
  of extension. Our `.rmxp` files contain a 64-character game ID, never shell code.
- Game folders alone open as directories. Automatic folder launch depends on
  matching `.cue`/`.m3u`; the explicit marker avoids that disc-specific behavior.
- NextUI quotes paths but uses fixed 256-byte command buffers. Registration
  rejects oversized UTF-8 commands, accounting for apostrophe escaping.
- NextUI exits before running the Pak, then restores its menu when it returns.

## Prepare on a computer (Python 3.11+)

Use a mounted SD card, not a live game directory. Supply a privately built and
reviewed runtime directory containing `engine`, `LICENSE.txt` and `stdlib/*.rb`.
Only the engine hash from the successful private Knight Blade test is accepted:
`33b15913859596645d4051bed403e6f0e0953e6d8366db3b06665a9a96ce73f3`.
This hash gate is not a dependency-license audit or a public release approval.

```sh
python3 scripts/rmxp_pak.py install --sd-root /media/SD --runtime /private/runtime
python3 scripts/rmxp_pak.py register --sd-root /media/SD \
  --game '/media/SD/Games/Knight Blade' --name 'Knight Blade'
```

Optional supervision from [PR #42](https://github.com/almighty-atlas/nextui-mkxp/pull/42)
can be included at initial installation with
`--session /private/rmxp-session.aarch64`. Only the reviewed cross-build hash
`3e1aa386ec7fbf08e3d4f97610604e5d97ddfbe09fee31168232a26288f1396d` is accepted.
The helper participates in the runtime checksum manifest. Without a per-game
`session.conf`, it supervises signals/child cleanup without monitoring buttons.
The target cross-build passed; actual H700 execution is still untested.

After verifying evdev codes on the device, a `session.conf` beside `mkxp.json`
may contain exactly three newline-terminated lines: `/dev/input/eventN`, first
keycode, second keycode. It is parsed as data, never sourced. There is no default
node or guessed code. The helper validates capabilities and uses a 1.5-second
hold / 3-second grace. Invalid settings fail before engine execution. Leave
this configuration absent until physical input is checked.

The original game requires `Game.ini`, `Data/`, `Graphics/`, `Audio/`.
Registration copies it once into `.userdata/h700/nextui-mkxp/<ID>/game/` and
writes a JSON configuration alongside it. Existing saves are copied initially;
subsequent saves remain exclusively in the private copy. The source is never
updated. Re-registering an existing ID is refused, preventing save overwrite.
IDs derive from the SD-relative source path; moving a source is not a migration.
Game updates require a deliberate, backed-up migration (not implemented here).
Allow enough SD space for a second copy plus 32 MiB reserve.

Provide legally obtained RTP at `Bios/RMXP/Standard/` and a licensed MIDI
soundfont at `Bios/RMXP/TimGM6mb.sf2` when the game needs them. Retain their
license notices privately. These files are never included in the source kit.

No Python is required on the handheld. Device paths use NextUI's
`/mnt/SDCARD` mount. The shell uses `USERDATA_PATH` and `SDCARD_PATH`.
The known-good H700 SDL/Mali/ALSA configuration is reused; other hardware and
rotated displays are untested. Physical A confirms, B cancels, Start opens the
game menu. Exit through the game's Shutdown command; the general exit chord
is tracked in #10. There is no MinArch menu, save state or instant resume.

Each game retains `run.log` and `previous.log`, each limited to 256 truncated
lines plus a final supervisor record (if present) and exit status. Engine output may contain private paths: review
before sharing. A lock prevents concurrent launches of the same game. After
power loss, verify no engine is running before manually removing the empty
`<ID>/lock` directory. No automatic stale-lock or save recovery is claimed.
Writable games are not a security sandbox for untrusted RGSS code.

## Source archive and uninstall

```sh
python3 scripts/rmxp_pak.py kit /private/rmxp-source.zip
python3 scripts/rmxp_pak.py validate /private/rmxp-source.zip
```

The validator permits exactly the launcher, preparation script and this guide;
it rejects duplicate/extra paths, symlinks, oversized entries and corrupt data.
Extract into a fresh directory, then run the preparation commands. This is a
source kit, **not** an engine-bearing drag-and-drop release.

To uninstall, remove only `Emus/h700/RMXP.pak` and the generated `.rmxp`
entries. Keep `.userdata/h700/nextui-mkxp/`: it contains saves. Back it up before
any optional manual removal. Leave original games and `Bios/RMXP` untouched.
The preparation commands refuse existing destinations. A failed copy can leave
an incomplete private directory without a marker; inspect before manual cleanup.
No `.system`, firmware, governor or service changes are performed.

## Explicit H700 checklist (German)

Verification on 2026-10-29:

| Level | Command/check | Result |
| --- | --- | --- |
| verified-on-host | `python3 -m unittest discover -s tests -v` | 10 tests PASS; synthetic engine only |
| verified-on-host | `sh -n pak/RMXP.pak/launch.sh` | PASS |
| verified-on-host | `git diff --check` | PASS |
| upstream-reported | pinned NextUI discovery/lifecycle source review above | contract identified |
| blocked | SSH to the owner device, 5-second connection timeout | connection timed out |
| untested | Pak discovery, real engine, error text, audio and display return | owner-device run required |

The tests exercise independent game copies, source-save preservation, literal
Unicode/apostrophe/shell-looking paths, oversized paths, missing assets, invalid
markers, symlink refusal, runtime tampering, locks, bounded logging, engine
failure status and the source-archive allowlist.

CI activation is **blocked**: GitHub rejected the workflow push because the
current credential lacks `workflow` scope. The inactive template is at
`.github/workflow-templates/pak.yml`. A maintainer with workflow write access
must move it to `.github/workflows/pak.yml` to automate these same offline tests.
No CI success is claimed.

1. Firmwareversion festhalten. Pak installieren, zwei eigene Spiele registrieren;
   mindestens ein Anzeigename mit Leerzeichen, Umlaut und Apostroph.
2. In NextUI „RPG Maker XP“ öffnen. Beide Einträge sichtbar? Beide starten?
3. Titel, Ton, Bewegung, Menü, Speichern und Shutdown prüfen. Kehrt NextUI zurück?
4. Beide erneut starten und laden. Originaldateien unverändert? Spielstände getrennt?
5. Fehlenden Game.ini-Pfad gezielt mit einer entbehrlichen Testkopie prüfen:
   lesbare Meldung und normale Rückkehr, keine beschädigten Spielstände.
6. Logs, Firmware und Beobachtungen dokumentieren. Host tests cannot satisfy this gate.
