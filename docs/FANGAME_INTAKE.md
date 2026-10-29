# Sage, Reborn and Team Rocket Edition intake (#52)

Update: the owner has now supplied all three archives. [Actual host inspection](FANGAME_HOST_INVENTORY.md)
records private extraction, data-only script inventory and two untested staged
candidates. The H700 connection is currently unavailable; no game has run there.
No bundle was downloaded by the agent. The sections below retain the original
**source-page-only triage**, before those private files were supplied.

[Machine-readable source observations](../build/h700-engine/fangame-intake.json)
use public landing-page URLs, not scraped temporary signed download links.
Landing-page versions/sizes are claims, not archive hashes or verified contents.
Knight Blade's existing private playability remains **100%** and says nothing
about these three games.

## Selected inputs

| Game | Owner-selected source | Preliminary choice and blocker |
| --- | --- | --- |
| Sage | [Selected MediaFire page](https://www.mediafire.com/file/03axirb5x2he3is/Sage+2.0.6.1++Public+Copy.zip) | Page lists ZIP 2.0.6.1, 273.64 MB, uploaded 2017-10-26. Get this exact ZIP privately; creator provenance, actual version/layout and native calls remain unknown |
| Reborn | [Developer download page](https://www.rebornevo.com/pr/download/) | Start with **Windows 19.5** for data inspection, not Windows execution. Do not silently substitute legacy 19.0. Page also offers Linux/AppImage and JoiPlay; contents still unknown |
| Team Rocket Edition | [LucksackGames creator page](https://lucksackgames.itch.io/pokemon-team-rocket-edition) | Page fetch returned HTTP 403. No access bypass, replacement mirror or release/version assumption. Supply the original creator download or its extracted private folder |

The Rocket entry is the exact LucksackGames project, not a similarly named GBA
ROM hack. A search snippet mentions an installer, but that is not a verified
format/version claim and is not used to choose an extractor.

### Why choose Reborn's Windows package first?

Our working engine is native **AArch64 mkxp-z**. The intent is to use compatible
RGSS/Ruby game data, not run `Game.exe`, Wine or a desktop Linux executable.
The developer page identifies the Linux launcher as `Game.AppImage`; "64-bit
Linux" does not establish AArch64 or H700 compatibility. Neither Windows nor
Linux bundles can supply a drop-in H700 engine without an ABI/source review.

The Windows package is therefore the provisional data-inventory candidate.
If its contents are installer-only, encrypted or depend on a special engine,
stop and inspect those requirements before deciding whether the Linux data
layout is more useful. No promise is made that it contains loose `Data/` files.
The offered JoiPlay build is Android-specific, not a NextUI binary; the
[developer FAQ](https://www.rebornevo.com/pr/gamefaq/) reports official JoiPlay
support since 19.5, not support for this H700 engine.

**Memory risk:** the official page requires **4 GB RAM+**, OpenGL 2.1+, a 64-bit
OS and 750 MB storage. The tested H700 has about **973 MiB physical RAM**.
This is a major feasibility warning, not proof either of failure or playability
with another runtime. Measure startup/RSS and stop safely on failure; no automatic
zram, sysctl, swap, driver replacement or firmware changes are allowed.

The FAQ also names **Game.rxdata** as Reborn's save file. The existing Knight
Blade overlay assumes standard `Scene_Save`/`Scene_Load` and Save1–Save4 slots.
Do not enable it for these games; Reborn in particular needs a reviewed adapter.
Existing personal saves must not be imported into the first smoke test.

## Owner handoff (one private file intake)

Download in your browser from the selected sources. Keep the original filenames
and note the exact release. Upload the archives to the private preparation-host
`incoming/` directory provided in the chat, **not** this repository or an issue.
An extracted private game folder is also acceptable if archive retrieval is
impossible; retain any original notices and version files. Do not run installers
on the H700 or post game assets, save files or signed download URLs publicly.

No hashes are invented here. On receipt, record SHA-256 and size of the exact
original bytes, mark the source/version relationship, and work on a separate
copy. Registration is blocked until file inspection below succeeds.

## Porting gates after files are supplied

1. **Safe offline inspection:** identify ZIP/installer/archive magic and limits;
   check paths, symlinks, FAT case collisions and free space before extracting
   into a fresh private directory. Never execute an installer or bundle launcher.
2. **Actual engine/layout:** locate `Game.ini`, data/scripts/assets, RGSS and
   Essentials version evidence, save paths, native libraries/Win32API and script
   engine extensions. Use the existing data-only inventory, not `Marshal.load`
   or Ruby execution against unreviewed game scripts. Packed scripts/resources
   are a blocker until a reviewed supported path is established.
3. **Compatibility decision:** compare actual APIs with our pinned mkxp-z and
   Ruby 3.1 profile. Keep per-game changes explicit, retain notices/provenance,
   and never copy copyrighted game code into Git. No speculative global patches.
4. **Private registration:** only when compatible, use the existing importer
   with a unique source path/ID and `--no-pause-menu`. Preserve the game's native
   save behaviour, not Knight Blade's slot assumptions. Keep downloads/network
   features disabled when their settings are actually known.
5. **H700 boot:** reviewed payload/hash and normal NextUI launch, no concurrent
   SSH graphics process. Record title/image, music, input and clean return;
   monitor memory rather than guessing that a slow start is OOM.
6. **Gameplay acceptance:** new game, map/movement/dialogue, menu, battle,
   game-native save/load, repeated cold start and NextUI return. Record every
   result per exact version. Only then consider an optional pause-menu adapter
   or any compatibility claim.

## Evidence and current result

- Sage page metadata read; payload hash and creator verification **unknown**.
- Reborn developer download/FAQ pages read; Windows candidate and memory/save
  constraints are **upstream-reported**, not host/device results.
- Rocket creator page: **HTTP 403**; search snippet not promoted to file evidence.
- All three: **NOT_TESTED on H700**, blocked by absent owner-supplied payloads.
- No game-bundle downloads, bypasses, game/installer execution or device writes.
