# Private state maintenance and diagnostic export (#11)

This is an **offline host tool**, compatible with the candidate state layout in
[PR #40](https://github.com/almighty-atlas/nextui-mkxp/pull/40). Python 3.11+ is
required on the preparation computer, not on H700. It neither launches games
nor modifies the engine/Pak. Device acceptance of #11 remains open.

## State and save compatibility

One state lives at `.userdata/h700/nextui-mkxp/<64-character-ID>/`:

- `game/`: private working copy, including game-defined saves anywhere within it;
- `mkxp.json`, `source.path`: launcher configuration and original source location;
- `data/`, `home/`: runtime settings and optional per-game state;
- `run.log`, `previous.log`: private logs from the Pak candidate;
- `lock/`: atomic directory lock shared with the Pak launcher.

The tool does not deserialize RPG Maker save data, rename saves, infer save
extensions or change their contents. A snapshot includes the **entire** state,
including empty directories and arbitrary game-specific save locations. This
costs additional disk space, but avoids guessing which files a game writes.
An engine-only replacement does not change the ID or state paths. Original
source moves and game upgrades require a separate migration plan; the #8
candidate derives IDs from source paths and refuses automatic re-registration.

## Private snapshot and validation

Stop the game and use a mounted card or a quiescent private copy of its state.
The shared lock prevents launches through the candidate while a snapshot runs.
Other programs that ignore the lock must also be stopped. No root, device SSH
or network access is needed.

```sh
python3 scripts/rmxp_state.py snapshot \
  --state '/media/SD/.userdata/h700/nextui-mkxp/<ID>' \
  --output '/private/backups/knight-before-update'
python3 scripts/rmxp_state.py verify \
  --backup '/private/backups/knight-before-update'
```

The output directory must be new, its parent must exist, and it must be outside
the repository and the source state. A reserve of 32 MiB is required beyond the
payload size. Symbolic links, special files, control characters and destination
paths containing `.system` are rejected. Manifests are limited to 16 MiB; a
larger file inventory is refused before copying. Files are copied and fsynced, hashes
checked, and the source inventoried again to detect changes. The final
`manifest.json` only appears after the copy is complete. Checksums establish
integrity, **not** authenticity: only restore your own trusted private backups.

Backups contain game assets, saves, configuration and potentially private log
data. Keep them private; never commit, publish or attach them to an issue.
The manifest also contains private filenames. Only the diagnostic JSON below
is designed for sharing.

If copying fails, the partial output remains for inspection, with no completed
manifest. The source and existing snapshots are not deleted. If the process is
terminated abruptly, a lock may remain. This tool never breaks a lock or kills a
process. Inspect it when the device is idle; stale-lock recovery is manual.
These checks do not make arbitrary game save writes atomic or repair corruption
that already exists in a save.

## Restore to a fresh destination only

```sh
python3 scripts/rmxp_state.py restore \
  --backup '/private/backups/knight-before-update' \
  --sd-root '/media/RECOVERY-SD'
```

The destination ID must not already exist. The tool never overwrites or removes
an existing save, even if it looks damaged. Restore to a fresh card/private
recovery directory first and compare. The complete payload is hash-checked
before its lock is removed. A failed restore remains locked and keeps its
partial data. Read-only source files become writable in the recovery copy;
their original permissions are unchanged. FAT32 permission behavior and
physical power-loss recovery still need hardware testing.

The original ID and configuration are retained. For play on another SD card,
retain the same `/mnt/SDCARD` device layout, original source-game location,
`.rmxp` entry, shared engine and required RTP/soundfont inputs. Those items are
not part of this state-only snapshot. Do not re-register over restored state.
Backup/restore is an explicit maintenance action, not a game save migration or
automatic quarantine mechanism.

## Privacy-safe diagnostic JSON

```sh
python3 scripts/rmxp_state.py diagnostics \
  --state '/media/SD/.userdata/h700/nextui-mkxp/<ID>'
```

Only a fixed set of keys and category names is emitted. Raw log lines,
usernames, paths, game names/IDs, IP addresses, URLs, payloads and credentials
are never echoed. Errors use fixed codes instead of exception messages that
could contain private paths. There is no raw/debug export mode. The scanner
reads at most the first 1 MiB and last 4 KiB of `run.log`; output size is bounded
independently of input size. Recognized warnings are hints, not complete log
analysis. Unknown or localized messages are not copied into the report.

| Outcome | Meaning |
| --- | --- |
| `returned_zero` | Final launcher marker says exit 0; not proof of successful gameplay or owner-selected Shutdown |
| `failed` | Final launcher marker says exit 1–127 |
| `signal_or_high_exit` | Exit 128–255; shell logs alone cannot distinguish a signal from an explicitly returned high exit code |
| `incomplete_or_unrecognized` | No valid final marker; interrupted or unfamiliar log |
| `locked_or_running` | Lock exists; may be a live launch or an interrupted maintenance operation |
| `no_log` | No run log available |

The #8 launcher still retains bounded **private raw** logs locally. This tool
makes their exported summary privacy-safe; it does not change runtime logging
defaults. A future runtime supervisor must record the actual wait status to
distinguish signals unambiguously. That remains open with #10/#11.

## Offline verification

2026-10-29: **16 tests PASS, verified-on-host**, including the optional
integration test against #40 at `a5c64a5`. `git diff --check`: PASS.
Hardware and CI results remain untested/blocked as described below.

```sh
python3 -m unittest discover -s tests -v
# Until PR #40 is merged, optionally exercise the candidate directly:
RMXP_PAK_SOURCE=/path/to/issue8/scripts/rmxp_pak.py \
  python3 -m unittest discover -s tests -v
```

All test saves/game files are generated synthetic data. Coverage includes
round trips, two independent games, read-only inputs, tampering, extra files,
path traversal, symbolic links, low disk space, source mutation during copy,
incomplete backup/restore, lock handling and private diagnostic text.
The integration test launches a synthetic engine four times across two
synthetic runtime versions and checks save preservation and isolation.
It is skipped when the candidate is absent and runs automatically once #40's
script is present. It does not execute mkxp-z or verify H700 behavior.

CI activation is still blocked by the available GitHub credential's missing
`workflow` permission. An inactive template is included; a maintainer can move
it into `.github/workflows/`. No CI or hardware PASS is claimed.

See [the grouped device session](RMXP_BATCH_TEST.md) for all deferred checks.
