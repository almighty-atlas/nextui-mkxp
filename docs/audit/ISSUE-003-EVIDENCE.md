# Issue #3 evidence report

Date: 2026-10-25. Level: **STATIC**, executed on a cloud Linux host.
Related: [SOURCES](../SOURCES.md), [distribution gate](../DISTRIBUTION_GATE.md).
No engine/toolchain build, release download, handheld access, game content,
firmware changes, R36S script execution, or Issue #4 work occurred.

## Repository and remote context

GitHub connector calls actually performed:

- `github_fetch` for `docs/PROMPTS/ISSUE-003.md`.
- `github_fetch_issue(repository_full_name="almighty-atlas/nextui-mkxp", issue_number=3)`:
  open; acceptance criteria inventory, STOP/GO, no R36S copying.
- `github_search_prs(repository_full_name="almighty-atlas/nextui-mkxp", query="repo:almighty-atlas/nextui-mkxp", state="all", topn=30)`:
  returned `issues: []` at inspection time; no existing PR to overlap.

Commands actually executed (paths are ephemeral audit workspaces):

```sh
git clone https://github.com/almighty-atlas/nextui-mkxp.git /workspace/nextui-mkxp
cd /workspace/nextui-mkxp
git status --short
git log -4 --oneline
git rev-parse main
cat AGENTS.md README.md docs/ROADMAP.md docs/ARCHITECTURE.md docs/SOURCES.md docs/TEST_PLAN.md
git switch -c docs/issue-3-provenance-audit
git clone --filter=blob:none https://github.com/mkxp-z/mkxp-z.git /workspace/scratch/mkxp-z
git clone --filter=blob:none https://github.com/Periko21/mkxp-z-r36s.git /workspace/scratch/mkxp-z-r36s
git -C /workspace/scratch/mkxp-z rev-parse HEAD
git -C /workspace/scratch/mkxp-z-r36s rev-parse HEAD
```

Results: initial working tree clean; main
`fa081c9f0cd4a36e6d84fdc54aa9b2c4fcf62250`; upstream engine
`37a04d14413454551a7b6aadbb4e93e67168accb`; R36S
`b665091c1ff571a7a468bbf33af2f7c803c75220`.

Inspected with `cat`, `head`, `sed` and `rg`: engine `README.md`, `COPYING`,
`meson_options.txt`, root/src/assets/shader Meson files, dependency wraps, MIT/BSD
embedded headers, R36S `README.md`, `NOTICE.md`, `LICENSE`, all five diffs,
source/dependency/package scripts, exitwatch header and commit history.
`git log --format='%h %an %s' --reverse` on the port reports nine commits by Pere.
Per-file `git log -1 --format='%H %an' -- <path>` results are retained in JSON.

An initial probe for `CMakeLists.txt` returned “No such file”; current engine
build uses Meson. Probes for `subprojects/libpng.wrap`, `bzip2.wrap` and
`libjpeg-turbo.wrap` also found no such top-level wrap. These are not evidence
that nested codecs are absent: SDL_image recursively fetches submodules.
`.gitmodules` at current engine pin was empty. No recursive dependency download
or build was run.

## Inventory and license evidence method

A local Python `configparser` extraction read every `subprojects/*.wrap`, copied
source/revision/hash/patch fields into `source-inventory.json`, and used
`hashlib.sha256(...read_bytes())` for each referenced local patch and each R36S
file. Result: **56 wraps, 138 patch references, 24 R36S file records**. Repeated
patch references remain associated with each dependency. No fetched implementation
was copied into this repository. To reproduce comparisons, clone the source
URLs above, check out the recorded full commits, parse the wraps and compare
fields, then recompute each patch/file SHA-256 at its inventory path. Upstream
archive hashes in JSON are declarations, not a download verification result.

Python `urllib.request.urlopen` fetched the five primary license texts in
[license-evidence.json](license-evidence.json); the JSON records exact URLs and
computed content SHA-256. `sha256sum /workspace/scratch/{openal,fluid,ruby,sdl,ssl}-license.txt`
confirmed those fingerprints. Source header grants were additionally read at:

- `https://raw.githubusercontent.com/kcat/openal-soft/1.24.3/al/buffer.cpp`
- `https://raw.githubusercontent.com/FluidSynth/fluidsynth/v2.5.0/src/synth/fluid_synth.c`

License URLs use tags; future retrieval must be compared with saved hashes, and
tags resolved to commits for a release. Full legal texts are not imported here;
this audit's links/hashes do not substitute for license copies in a binary release.

## Verification matrix

| Command / check | Level | Result / limit |
| --- | --- | --- |
| `python3 scripts/check_provenance.py` | STATIC | PASS: 56 wraps, 138 patch references, 24 R36S records; required fields, hash syntax, pins, blocked states and relative links checked offline |
| Independent comparison to cloned upstream metadata and recomputed file hashes | STATIC | PASS; recorded below via audit-time Python comparison; no upstream archive checksum verification |
| `git diff --check` | STATIC | PASS; whitespace only |
| New `.github/workflows/provenance.yml` | CI | NOT_TESTED at report creation; configured for push/PR; no claim of CI success |
| Engine build / ELF / relink or replacement | HOST | NOT_TESTED; deliberately outside scope |
| Device, firmware, performance, games | H700 | NOT_TESTED; no access attempted |
| R36S behavior | OTHER DEVICE | Upstream-reported only; no independent run |

Structural checks validate records, not rights or completeness of the selected
build. All 56 wraps include options/platforms that may never be built; their
inclusion is not a claim that they are linked. System libraries, nested codec
revisions, embedded asset grants and unknown license entries remain blocking
if selected. See the gate for human review, source/relink artifacts and the
precise next unblocked M0 step.
