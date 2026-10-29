# Implemented-work integration review — 2026-10-29

The owner explicitly requested merging implemented work and closing completed
issues. PR #47 integrates the original PR histories rather than squashing away
their individual evidence. Existing local work and private device data were not
changed. This is a source integration, not authorization to publish binaries.

## PR disposition

| PRs | Integrated deliverable |
| --- | --- |
| #19, #20 | Provenance STOP/GO audit and read-only H700 baseline (already merged) |
| #21 | Native-Pak architecture and marker discovery decision |
| #23, #25, #27 | Original GLES spike, toolchain identity, Linux-4.9 sysroot and Mali link experiments |
| #28, #29 | Read-only runtime metadata and host-only libc validation |
| #30 | Actual owner-observed H700 triangle and NextUI-return evidence |
| #31, #32 | Offline build-input preflight and Ruby runtime/extension pipeline |
| #33, #34 | Engine source lock/build evidence, ABI validator and H700 loader PASS |
| #35, #37, #39 | Engine smoke, private Knight Blade inventory and 100% playability evidence |
| #40, #41, #42 | Private Pak, isolated state tooling and native session supervisor |
| #43, #44 | Repository guard and offline archive builder/verifier |
| #46 | Menu-button pause overlay, using the game's own Save/Load screens |

Earlier NOT_TESTED/BLOCKED reports retain their historical scope. Current
hardware results are in [the batch checklist](RMXP_BATCH_TEST.md),
[Knight Blade boot](KNIGHT_BLADE_BOOT.md) and [pause menu](RMXP_PAUSE_MENU.md).
The weighted Knight Blade playability milestone remains **100%**; it is not a
public-release, full-playthrough or Pokémon compatibility percentage.

## Issues ready to close after integration

| Issue | Evidence / completed scope |
| --- | --- |
| #1 | Read-only probe, baseline, runtime metadata, explicit unknowns |
| #2 | Architecture ADR and device-tested native marker discovery |
| #3 | Source/license inventory and explicit unresolved distribution STOP gate; closure means audit delivered, not rights granted |
| #6 | Automated ABI negative tests, provider closure and actual loader PASS |
| #7 | Asset-free graphics/audio/input fixture, actual H700 logs and owner observations |
| #8 | Pak discovered, launches, errors safely, preserves original game and saves during upgrade/reboot |
| #9 | Guard and forbidden-path fixtures run through the existing active root-test workflows |
| #10 | Documented configurable mappings, physical chord and cleanup, bounded synthetic forced-exit fallback |
| #22 | Owner saw the moving GLES triangle and responsive NextUI return |
| #24, #26 | Bounded host-only feasibility experiments, pinned artifacts and exact remaining blockers |
| #36 | Synthetic-tested private inventory with sanitized requirements/evidence |
| #38 | Owner-confirmed title, music, first map and gameplay, with sanitized logs |
| #45 | Host-tested overlay and owner-confirmed Menu/Continue/Save/Load/Quit |

## Issues kept open

- **#4 / #5:** successful private builds are recorded, but complete clean-room
  bootstrap/build reproduction and exact input/receipt closure remain open.
- **#11:** two-instance independent saves and in-game load of a restored
  snapshot remain unobserved. Host tests and bit-identical backup/restore do
  not replace those checks. Raw logs are private; only allowlisted diagnostic
  exports are safe to share.
- **#12–#15:** exact legally supplied Pokémon game versions, requirements,
  hardware gameplay and performance results are not available.
- **#16:** no public archive/source/relink kit has been approved. The human
  license, source, relink, provenance, approval and exact-engine H700 release
  gates remain required; archive tooling alone does not complete this issue.
- **#17:** no tested public-release installation guide or tagged release.
- **#18:** ongoing master tracker, updated to reflect this review.

## Verification (verified-on-host)

Executed in the existing pinned Debian tools image
`sha256:1c4ddd5655ad020d5e320e2181a04e4356af7c0e70f2be3cd5e901657cd8596b`,
network disabled, all capabilities dropped, no-new-privileges, uid/gid 1000,
read-only repository/Ruby mount and bounded writable tmpfs. No compiler or
package was installed on the handheld; no new device test was performed.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` | 257 run, 256 PASS, 1 skipped (optional BusyBox unavailable) |
| `python3 -m unittest discover -s scripts/tests -v` | 12 PASS |
| `python3 -m unittest discover -s scripts/issue_26_tests -v` | 27 PASS |
| `python3 -m unittest discover -s spikes/h700-video/tests -v` | 7 PASS |
| `python3 -m unittest discover -s spikes/h700-stock-video -v` | 19 PASS |
| `python3 -I scripts/issue_26_test.py` | 32 PASS |
| `ruby -w tests/pause_menu_test.rb` (Ruby 3.1.3) | 13 runs, 45 assertions PASS |
| `python3 scripts/check_provenance.py` | PASS: 56 wraps, 138 patch references, 24 R36S records |
| `python3 scripts/repo_guard.py` | PASS: index-only asset/secret/binary/link checks |
| `git diff --check` | PASS |

Review fixes: escaped the probe's awk regex delimiter for BusyBox; checked
both archive outputs before writing (including existing checksum sidecars);
bounded malformed ELF version/string-table parsing; rejected noncanonical ZIP
paths and `$ORIGIN` prefix/parent escapes; kept manifest validation active under
Python optimization; added four negative tests. Original firmware observations
are not promoted to new hardware tests. CI results are recorded on PR #47.
