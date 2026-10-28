# Codex / contributor instructions

Read `README.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md` and the assigned GitHub issue **before** changing files.

## Workflow

### Active first-game roadmap

For ongoing H700 work, maintain `docs/KNIGHT_BLADE_ROADMAP.md` and
`build/h700-engine/knight-blade-progress.json`. Report the current weighted
percentage; 100% means Knight Blade meets the on-device playability checklist,
not merely a successful build. Keep the README and general roadmap percentage
consistent. Work through unfinished tasks autonomously; report missing access,
legally supplied game/RTP files, required hardware observations or authorization.
Never mark hardware work complete from host-only tests.

1. Work on exactly one issue and a short-lived branch from current `main`. Link the issue in the PR (`Refs #N`, or `Fixes #N` only if all acceptance criteria are met).
2. Inventory existing code, upstream versions, hardware assumptions and tests before implementation. Prefer the smallest reviewable change; don't silently broaden scope.
3. Provide concrete commands and their outputs. Distinguish `verified-on-H700`, `verified-in-CI`, `verified-on-host`, `upstream-reported`, `untested`, and `blocked`.
4. Make safe offline/static tests run automatically. Hardware-dependent checks go in an explicit human test checklist, **never** claim they ran in a cloud runner.
5. Produce a PR with summary, files changed, verification matrix, risks, reproducibility, and next step. Do not merge by default.
6. If blocked, publish a narrow evidence report and smallest actionable follow-up instead of implementing speculative fixes.

## Safety and correctness

- **Never commit or distribute game assets**, RTP files, save games, ROMs, official RPG Maker executables, Pokémon sprites, license keys or proprietary binaries.
- Keep all cross-build downloads pinned by immutable commit/tag and checksum where possible. No unreviewed curl-to-shell, silent sudo, host-wide changes or privileged CI.
- Treat the RG35XX Pro + NextUI H700/aarch64 environment as a distinct platform from ArkOS RK3326/armhf. Verify ABI, linker, glibc, GPU, SDL, audio and input on the target.
- Prefer standalone native mkxp-z initially. NextUI MinArch lacks OpenGL libretro APIs; do not claim game switcher, save states, instant resume or standard in-game menu integration in a standalone Pak.
- **No firmware partition writes, partition formatting, flash operations, global kernel tweaks, destructive cleanup, or automatic zram/sysctl modifications** without a separate explicit approval and rollback plan.
- Launcher must preserve game files and saves, quote paths, avoid writing inside the engine bundle where practical, maintain per-game isolation and reliably restore process state on exit.
- No scraping or automatically downloading copyrighted fan-game bundles.
- Respect upstream licenses (including R36S reference code, mkxp-z, NextUI and bundled dependencies). Do not copy files until provenance/license is documented.
- Default user-facing documentation in English; provide German human hardware test steps when useful.

## Definition of Done

- All issue acceptance criteria satisfied with links to evidence.
- Cross-build is reproducible or explicitly blocked with a concrete reason.
- No secrets, personal information, game assets or undocumented binaries in tracked files/artifacts.
- CI/static checks pass; on-device features cannot be marked verified without device test logs and firmware version.
- New limitations documented in `docs/COMPATIBILITY.md`.
