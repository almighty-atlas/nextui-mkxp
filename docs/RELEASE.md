# Release archive builder and offline verifier (#16)

Status: **verified-on-host** tooling only. **No release archive has been
published or approved.** The [distribution gate](https://github.com/almighty-atlas/nextui-mkxp/pull/19)
(#3) is BLOCKED for all binary releases, and H700 release acceptance is open.

`scripts/release_archive.py` (Python 3, no dependencies, no network) builds a
deterministic `.zip` from a reviewed stage directory and verifies any archive
offline. It reports two separate results:

| Result | Meaning |
| --- | --- |
| `STRUCTURE=PASS` | Layout, checksums, notices, script syntax and target ELF ABI are consistent |
| `RELEASE_GATE=GO` | Every human gate in the manifest is GO, and the H700 gate is bound to this exact engine hash |

Exit codes: `0` structure PASS and gate GO; `3` structure PASS, gate BLOCKED
(a reviewable candidate, **not** publishable); `1` structural findings;
`2` usage/I/O error, including an already existing output file.

```sh
python3 scripts/release_archive.py build --stage /private/stage --out /private/RMXP-<version>.zip
python3 scripts/release_archive.py verify /private/RMXP-<version>.zip
python3 scripts/release_archive.py --json verify /private/RMXP-<version>.zip
sha256sum -c /private/RMXP-<version>.zip.sha256
```

`build` validates the complete archive in memory and writes nothing on
failure. It never overwrites an existing archive or `.sha256` sidecar. Zip
entries are sorted, use a fixed 1980-01-01 timestamp, Unix mode 0755 for
`binary`/`script` roles and 0644 otherwise, independent of stage mtimes and
permissions. Byte-identical output assumes the same Python/zlib version;
member hashes are independent of compression.

## Archive layout

The zip root mirrors the SD card root. **Only** `Emus/h700/RMXP.pak/` is
allowed. Archives never contain `.userdata/`, `.system/`, `Roms/`, saves,
games, RTP, RGSS data, Windows executables/DLLs, audio, keys or nested
archives. Symlinks, special files, encrypted members, `..`, absolute paths,
backslashes and case-insensitive name collisions (FAT32/exFAT) are rejected.

```text
Emus/h700/RMXP.pak/
  launch.sh                      script
  engine                         binary (AArch64)
  rmxp-session                   binary, optional (#42)
  stdlib/**                      data (Ruby stdlib)
  keybindings.mkxp1, LICENSE.txt data/license
  SHA256SUMS                     launcher runtime checks
  release/manifest.json
  release/THIRD_PARTY_NOTICES.md
  release/BUILDING.md
  release/LICENSES/*
```

`SHA256SUMS` must cover every Pak file except itself and
`release/manifest.json` (which lists the hash of `SHA256SUMS`, so including
it would be circular).

## Manifest (`release/manifest.json`)

```json
{
  "schema": 1,
  "version": "0.1.0-beta",
  "target": {"arch": "aarch64", "interpreter": "/lib/ld-linux-aarch64.so.1",
             "glibc_max": "2.28", "allowed_needed": ["libc.so.6", "..."]},
  "files": [{"path": "Emus/h700/RMXP.pak/engine", "sha256": "...", "role": "binary",
             "license": "GPL-2.0-or-later", "license_file": "Emus/h700/RMXP.pak/release/LICENSES/...",
             "source": "mkxp-z@<commit>"}],
  "gates": {"license_review": {"state": "GO", "reviewer": "...", "date": "YYYY-MM-DD", "evidence": "..."}}
}
```

The license values above are placeholders; the actual elections come from the
#3 review. Every archive file must be listed exactly once with its SHA-256 and
one of the roles `binary`, `script`, `data`, `config`, `license`, `notice`,
`doc`. Executable, script, data and config files require a declared license.
Binaries also require a license text inside the archive and a source
reference. An ELF in any non-binary role is rejected.

For every `binary`, the verifier parses the ELF itself: ELF64 little-endian
AArch64, exact `PT_INTERP`, non-executable `GNU_STACK`, `GLIBC_*` version
requirements no newer than `glibc_max`, no `GLIBC_PRIVATE`, `NEEDED` libraries
within `allowed_needed`, and `RPATH`/`RUNPATH` entries starting with `$ORIGIN` only.
These checks are static. They do not prove that `dlopen` targets, Mali/GLES
symbols or device library versions work at runtime.

## Release gates

The verifier requires these gates, mirroring the #3 distribution gate. Each
needs `state: "GO"`, a non-empty `reviewer`, an ISO `date` and `evidence`:

| Gate | Human evidence required |
| --- | --- |
| `license_review` | #3 file/patch grants, combined GPL/OpenSSL review |
| `corresponding_source` | Matching `source/` archive mapped to the binary hashes |
| `relink` | Verified LGPL relink or replacement route |
| `binary_provenance` | Reviewed file list, link map, `readelf` and notice mapping |
| `release_approval` | Named reviewer sign-off, no unresolved rights |
| `h700_acceptance` | Additionally: `level: "verified-on-H700"`, `device: "RG35XX Pro"`, `firmware`, `engine_sha256` equal to the archived engine, and `results` R1–R7 all `PASS` |

Host tests, CI or this tool cannot create GO evidence. A GO manifest only
records what humans assert, so reviewers must check the cited evidence.
Changing the engine invalidates the H700 gate automatically through the hash
binding.

## Upgrade, rollback and uninstall

The archive contains only the Pak directory, so extracting it never touches
saves, game folders, `.userdata/` or NextUI system directories. Per-game state
from #40 lives in `.userdata/h700/nextui-mkxp/<ID>/` and launch markers keep
the stable path `Emus/h700/RMXP.pak/launch.sh`.

1. Quit every game. Verify the archive offline (`verify` plus `sha256sum -c`).
2. Back up each game's state with `rmxp_state.py snapshot` (#41) to a computer.
3. **Upgrade:** move the existing `Emus/h700/RMXP.pak` out of `Emus/` to
   `RMXP-rollback/<old-version>/RMXP.pak` on the SD card. Do not delete it.
   Extract the new archive at the SD card root. A previously installed
   `rmxp-session` or per-game `session.conf` is not migrated implicitly:
   reinstall only reviewed files.
4. **Rollback:** move the new `Emus/h700/RMXP.pak` to
   `RMXP-rollback/<new-version>/`, then move the previous version back.
5. **Uninstall:** move `Emus/h700/RMXP.pak` off the card. Game folders,
   launch markers and `.userdata/h700/nextui-mkxp/` remain until removed
   manually after a backup.

Save formats written by a newer engine may not be readable by an older one.
Restore a pre-upgrade snapshot into a fresh state ID (#41) instead of
overwriting.

## H700 release checklist (deutsch, R1–R7)

Nur auf einem echten RG35XX Pro mit notierter NextUI-Version. Ergebnis je Punkt
PASS/FAIL/BLOCKED. Nur wenn alle Punkte PASS sind, darf `h700_acceptance` auf GO gesetzt werden.

| ID | Schritt | Erwartung |
| --- | --- | --- |
| R1 | Archiv am PC mit `verify` und `sha256sum -c` prüfen, auf SD-Wurzel entpacken | Nur `Emus/h700/RMXP.pak/` neu; nichts in `.userdata`, `Roms`, `.system` geändert |
| R2 | Eigenes Testspiel registrieren und aus NextUI starten | Titelbild, Ton und Steuerung funktionieren |
| R3 | Im Spiel speichern, über das Spielmenü beenden | Rückkehr zu NextUI, Ton aus, Menü bedienbar |
| R4 | Erneut starten und Spielstand laden | Gespeicherter Stand vollständig vorhanden |
| R5 | Upgrade laut Abschnitt oben auf ein zweites Kandidatenarchiv | Spielstand unverändert ladbar |
| R6 | Rollback auf die vorherige Version | Start und Laden funktionieren wieder |
| R7 | Gerät regulär neu starten, erneut starten und laden | Pak dauerhaft vorhanden, richtiger Spielstand |

## Verification (2026-10-29)

- **9 host tests PASS** (`python3 -I -m unittest discover -s tests -v`) with
  synthetic ELF64 fixtures and placeholder license text. They cover the blocked
  candidate, determinism across mtimes and permissions, exact-engine H700 binding,
  forbidden/outside paths, traversal, symlinks, case collisions, checksum and
  `SHA256SUMS` drift, required files, nine ABI rules, undeclared binaries, shell
  syntax, no-write-on-failure and no-overwrite.
- **ELF parser cross-check (verified-on-host):** run read-only in the
  network-disabled tools container against the private staged engine
  (`33b15913…73f3`, identical to the #40 pin) and #42 supervisor
  (`3e1aa386…396d`). Neither produced findings with `glibc_max` 2.28. The
  engine was correctly flagged with 2.17. `readelf` agrees: engine
  `RPATH [$ORIGIN]` and max GLIBC_2.28; supervisor no RPATH and GLIBC_2.17.
  Binaries were not copied or published.
- GitHub Actions: inactive template only (missing `workflow` scope).
- No archive built from real private binaries, nothing distributed, H700 untested.
