# Owner-supplied fangame archives: actual host inspection (#52)

2026-10-29, **verified-on-host**. The owner placed the three archives privately
on the preparation host. We hashed those exact bytes, unpacked separate copies,
and inspected scripts **as data only**, without executing Ruby, a game EXE or
an installer. No game bundle was downloaded by the agent. All original files
and existing H700 saves are untouched.

[Exact hashes, sizes, layouts and counts](../build/h700-engine/fangame-host-inventory.json)
are safe metadata, not game content. Detailed private reports/output trees must
not be committed, attached or distributed. Earlier
[landing-page triage](FANGAME_INTAKE.md) is retained as historical evidence.

## Results and concrete next steps

| Game | Observed payload | Preparation / remaining gate |
| --- | --- | --- |
| Sage | ZIP, 308,066,477 expanded bytes, RGSSAD v1; 209 script-table entries | Separate SD-shaped candidate prepared. Review Windows API, Flash and GIF branches, then real H700 boot |
| Reborn 19.5.0 Windows | ZIP, 772,599,834 expanded bytes; one script-table loader plus 193 external Ruby files | Held for binding/config compatibility review; not blindly registered with Knight Blade defaults |
| Lucksack Team Rocket Edition | RAR5 containing one PE32 self-extractor, then a CAB; 211 script-table entries in RGSSAD v1 | CAB unpacked as data; separate candidate prepared. Review Windows/GIF branches, then real H700 boot |

Every H700 result remains **NOT_TESTED**. The device SSH connection timed out;
no candidate was copied there and no running game or system service was touched.

**Later device session:** connectivity returned and both candidates were
[installed and checksum-verified](FANGAME_DEVICE_TEST.md) into new paths.
The preceding paragraph records the initial host-only round; the new file
checks do not establish that either game boots or plays. Reborn remains held.

### Reborn is not a drop-in Knight Blade profile

The supplied configuration uses 512×384, extra binding names d/e/f and a patch
path. It contains trailing commas (JSON-with-comments-style syntax), so it must
not be loaded with `eval` or silently interpreted as ordinary strict JSON.
Game scripts reference Input D/E/F and extended Input/Graphics/System methods.
The pinned native binding does not export D/E/F itself. Some methods are Ruby
wrappers, so identifier counts alone do not prove that each native API is absent.
Review and test the actual fallback/mapping semantics before adding an adapter.

The source also references socket/HTTP/Discord and Windows accessibility DLLs;
those can be conditional paths, not necessarily Linux startup requirements.
Do not execute bundled Windows DLLs or guess that all such calls must be removed.
Keep online features disabled only through settings actually verified in the game.
The developer's 4-GB-RAM requirement remains a major risk for H700's ~973 MiB.

### Sage and Rocket keep their packed assets

The native mkxp-z source at `37a04d1` registers RGSS1 and mounts `Game.rgssad`
before the loose game directory (`src/sharedstate.cpp`, `src/crypto/rgssad.cpp`).
We validated bounds and names and decoded only the script table in memory for
counts; no general asset/source dump is produced.

Some expected asset directories exist only inside the archive. The candidate
preparer adds **empty mount-point directories only in its new private source
copy**, and only for roots verified in the packed index, so the existing launcher
can check its layout. It does not invent missing loose data, unpack copyrighted
assets into Git, change the original archive or claim runtime compatibility.

Both candidate registrations explicitly disable the standard Knight Blade
overlay. Save formats/scene classes require a game-specific adapter. Native
supervision/quit mapping can be enabled only after current device/firmware and
event codes are reconfirmed; no default unknown hardware setting is guessed.

## Rocket wrapper: no Windows execution

The RAR contained `6-18-20.exe` (not proof of a release date). Innoextract
correctly rejected it as a non-Inno installer. A pinned private 7-Zip tool
identified a CAB at offset **83,456**, physical size **111,743,331** bytes.
The CAB header/reserved fields/version/counts and exact end-of-file bounds were
checked before copying that byte range into a private file. Libarchive then
unpacked its 1,005 entries. No installer startup, Wine or Windows runtime was used.

[Tool provenance](../build/h700-engine/private-extractor-tool-evidence.json):
Debian packages were acquired from the signed, immutable 20261020 snapshot and
their SHA-256 values recorded. They were unpacked into a private prefix, not
installed on the host or H700; no package maintainer scripts ran. Final RAR/CAB
reading uses libarchive in the existing image. No tool binaries are distributed.

## Reusable host commands

Run inside the existing pinned image with read-only inputs/source, a fresh
private writable output, no network, uid/gid 1000, no-new-privileges, dropped
capabilities, 2 CPUs / 4 GiB. ZIP works with Python alone; RAR/CAB needs the
reviewed libarchive from that image.

```sh
# Hash must be the recorded owner-supplied archive, never a moving URL:
python3 scripts/rmxp_private_archive.py /private/input.zip \
  --sha256 EXACT_SHA256 --output /private/fresh-unpacked

python3 scripts/rmxp_fangame_audit.py --game /private/unpacked-game \
  --report /private/fresh-audit.json

# Only for reviewed RGSSAD-v1 inputs; creates no engine or device execution:
python3 scripts/prepare_packed_rmxp.py --game /private/unpacked-game \
  --game-archive-sha256 EXACT_GAME_RGSSAD_SHA256 \
  --sd-stage /private/fresh-sd-stage --name 'Private Candidate'
```

Archive extraction validates paths, special files/links, duplicate/FAT case
collisions, sizes and free space before writing. Outputs never replace an existing
tree; partial owned output is retained after failure, not deleted. Extracted
executables have no execute bits. The minimum 5-GiB reserve keeps 1-GiB headroom.
Packed index names are bounded below the native reader's 512-byte name buffer;
script-table decoding/inflate and aggregate source scans have explicit limits.
Regex counts include comments/conditional paths and are not a complete call graph.

## Next hardware session

Once SSH is reachable, validate the installed engine/firmware and stage only
fresh game/source/ID/marker paths. Start via the normal NextUI handoff, never
concurrently over SSH while the menu owns the display. First collect exact
startup/error and memory evidence, then ask for image/audio/control observations.
Review any actual first failure before implementing an adapter. Keep Knight Blade
as the regression case; its private playability remains **100%**.
