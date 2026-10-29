# Knight Blade: owner-provided files and RTP requirements

2026-10-28 · Refs #36 · Stacked on PR #35.
**Knight Blade: 88%. Inventory complete; game boot not yet attempted.**

Level: **verified-on-host** (private build host). No game file reached the
device, no engine ran the game, and the Windows installer was never executed.

## Provenance

The device owner designated both files as free official downloads. They were
fetched once on request (no scraping, no bundles) and reproduced byte-for-byte
on a second host. They stay in a private mode-700 directory, outside Git.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `knight-blade-howling-of-kerberos.zip` (rpgmakerweb.tkool.jp) | 17,949,792 | `a47c9cf1eaa466fc0fcd5e4fff0143881d318a71424fe1fab823aa95acaac58c` |
| `xp_rtp104e.exe` (assets.rpgmakerweb.com) | 22,994,937 | `b3bd20ad7f413b40ac233aafd2e061de1dc429c2eadb59d0b3157ba3c47f16b2` |

**Game:** unencrypted RPG Maker XP project `KN_E` ("KNight-Blade Howling of
Kerberos"), 757 entries, no absolute/`..` paths or symlinks, `Game.ini` asks
for `RGSS102E.dll` and `RTP1=Standard`. The RGSS DLL is not included and is
not needed: mkxp-z replaces it. `Game.exe` is unused.

**RTP:** Inno Setup 5.2.3 "RGSS-RTP Standard". `innoextract` 1.9 (pinned
Debian snapshot, private derived image, no network, read-only, no
capabilities) extracted only `app/Graphics` and `app/Audio`: 881 media files,
no DLL/EXE/symlink. The six proprietary RGSS DLLs were deliberately excluded.

## Inventory method

[`scripts/rgss_inventory.py`](../scripts/rgss_inventory.py) parses Ruby
Marshal 4.8 with a data-only reader (no object construction, depth/link/
truncation guards), walks the database, maps, common events, troops and move
routes, and also picks up literal `RPG::Cache`/`Audio.*_play` names in
scripts. Names resolve case-insensitively against the game, then the RTP.
Script source is scanned for platform-specific features but never committed.
[Host tests](../tests/test_rgss_inventory.py) use synthetic Marshal data only.

## Results

- 583 distinct references: **520 game, 62 RTP, 1 missing**, 0 case mismatches.
- RTP-only: 15 BGM, 2 BGS, 2 ME, 32 SE, 6 animations, 1 panorama, 4
  transitions. **The RTP is required.**
- Resolved formats: PNG 449, JPG 24, WAV 44, OGG 37, **MIDI 28** (11 game
  BGM, 15 RTP BGM, 2 RTP ME). No MP3/WMA.
- Missing: picture `kn_fortcity`, used from a common event, absent from game and
  RTP. A pre-existing data gap; it only matters if that event runs.
- 91 scripts (600,042 bytes): no `Win32API`, shell calls, `resize_screen` or
  font override. File writes are the standard `Scene_Save`; saves are
  `Save1..4.rxdata` relative to the working directory.

[Evidence record](../build/h700-engine/knight-blade-inventory.json).

## Requirements for the first game boot

1. Supply the extracted Standard RTP through mkxp-z's `RTP` config from a
   private device path; never copy RTP into the repository or the Pak.
2. Configure `midiSoundFont`. Without it, 28 BGM/ME tracks stay silent (the
   smoke log already warns "No soundfont specified"). Choose a soundfont with
   documented license and modest RAM use; measure CPU/RAM on H700.
3. Keep `pathCache` enabled for games (only the smoke fixture disables it).
4. Choose the save location deliberately: RGSS writes `Save*.rxdata` into the
   working directory. Preserve existing saves; never write into the engine bundle.
5. Expect the default fallback font (smoke log: "Primary font not found:
   Arial"); readable text must be checked on device.
6. Controls: mkxp-z's default mapping makes physical A act as Cancel and leaves
   Start/Select unbound (see [engine smoke](H700_ENGINE_SMOKE.md)).
