# Knight Blade first boot on H700: PASS

2026-10-29 · Refs #38 · Stacked on PR #37 ([inventory](KNIGHT_BLADE_INVENTORY.md)).
**Knight Blade: 98%. Boot and representative gameplay verified-on-H700
(NextUI-20261013-0, 39a06de); load after a cold start not yet tested.**

## Result (owner-launched, run-ljOadD)

The owner reports: title screen, music and sound effects work; everything works
flawlessly with no restriction noticed; saving, movement, battles and the main
menu work. Logs: Mali-G31 GLES 3.2, path cache built, ~441 s run, in-game
shutdown, engine exit 0, `BOOT_RUNNER_EXIT_OK`. `Save1.rxdata` (126,258 bytes)
was written into the private game copy. Peak RSS 209,752 kB (89 samples).
[Sanitized log](evidence/2026-10-29-knight-blade-boot.txt).

Non-blocking warnings: Arial/Arial Black not found, the embedded fallback font
is used (text looked fine to the owner); vendored FluidSynth prints stub
messages for `fluid_file_test`/`fluid_stat` but the soundfont loads and music
plays; one MIDI instrument is substituted from bank 0.

## Layout (private, owner device only)

| Location | Content |
| --- | --- |
| `/tmp/nextui-mkxp-kb-boot-v1` | engine, pure-Ruby stdlib, `run.sh`, `mkxp.json`, generated `keybindings.mkxp1` (hash manifest) |
| `/mnt/SDCARD/.userdata/h700/nextui-mkxp-test/games/KN_E` | owner-provided game; RGSS saves (`Save*.rxdata`) land here |
| `…/nextui-mkxp-test/rtp/Standard` | Graphics/Audio from the RTP installer (no DLLs) |
| `…/nextui-mkxp-test/soundfonts` | TimGM6mb.sf2 (GPL-2, Debian `timgm6mb-soundfont` 1.3-5) + copyright |
| `…/nextui-mkxp-test/data` | `XDG_DATA_HOME`: mkxp-z data path with our keybindings |
| `Tools/h700/Knight Blade Boot Test.pak/launch.sh` | sole new Tools file, points to the `/tmp` stage |

Both manifests passed on the device (1,640 game-input files; FAT32-safe names,
no case collisions). Nothing here is committed or distributable. The engine
stage is built by `scripts/prepare_h700_engine_smoke.py --fixture knight-blade-boot`.

## Configuration choices

- `pathCache` on (FAT32 is case-insensitive anyway), symlinks off, no JIT,
  no settings/reset menu, MIDI chorus/reverb off to save CPU.
- Controls from [`keybindings.json`](../tests/hardware/knight-blade-boot/keybindings.json),
  encoded by `scripts/mkxp_keybindings.py` in mkxp-z format 3. NextUI's SDL
  reports physical A as SDL B, so: **A = confirm, B = cancel, Start = menu**,
  X/Y = RGSS A/X, L/R, D-pad and left stick move. Menu and Select are unbound.
- The runner verifies both manifests, uses a clean environment, refuses
  display contention, samples engine RSS every 5 s to `mem.log` and has a
  30-minute watchdog. Exit code 0 means only that the engine returned.

## Human device checklist (German)

1. Gerät wach lassen, SSH aktiv. Mittlere Lautstärke.
2. **Tools → Knight Blade Boot Test** starten. Die erste Ladezeit kann einige
   Sekunden dauern (Dateiprüfung + Spielstart).
3. Erscheint der Titelbildschirm? Läuft Titelmusik (MIDI)?
4. **A** = bestätigen, **B** = abbrechen, **Start** = Menü. „New Game“ wählen.
5. Erste Karte: Figur mit D-Pad/Stick bewegen, ein Gespräch/Ereignis
   ausprobieren. Ruckelt es? Stimmen Bild, Text und Ton?
6. Beenden: im Spiel **Start → End Game → Shutdown** (bzw. im Titel
   „Shutdown“). Kommt NextUI normal zurück?
7. Berichten: Titel / Musik / Neues Spiel / erste Karte / Tasten / Rückkehr,
   sowie Fehlermeldungen oder Hänger. Gerät danach anlassen (Logs).
