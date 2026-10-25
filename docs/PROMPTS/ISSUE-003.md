# Codex task — GitHub Issue #3 (M0 licensing and provenance)

## Goal

Audit whether and how we can legally and reproducibly reuse **mkxp-z** and the **R36S reference port** for a new standalone H700 / NextUI `RMXP.pak`. **No engine build, no firmware modifications and no game files** in this issue.

## Instructions for Codex

```text
Work in repository almighty-atlas/nextui-mkxp on GitHub Issue #3
[M0] Audit upstream licenses, source provenance and redistributable artifacts.

Read the issue and AGENTS.md, README.md, docs/ROADMAP.md,
docs/ARCHITECTURE.md, docs/SOURCES.md and docs/TEST_PLAN.md.

Inspect current main and PRs. On a fresh issue branch:
1. Inspect license and provenance of mkxp-z and relevant portions
   of Periko21/mkxp-z-r36s, at pinned source commits; distinguish
   original code, third-party patches and bundled dependencies.
2. Build a source/dependency/patch inventory with exact upstream URLs,
   revisions, SPDX identifiers or explicit unknowns and obligations.
3. Analyze GPL/LGPL, linking and source/relinking obligations, especially
   OpenAL Soft, FluidSynth, Ruby, SDL2 and optional HTTPS/OpenSSL.
   Document obligations conservatively; don't guess at legal certainty.
4. Add a concrete distribution gate: what source, attribution, notices,
   instructions and build artifacts would be necessary for any binary release.
5. Highlight uncertainties requiring human review. Do not import, vendor
   or distribute any code/binary with unclear rights.
6. Update docs/SOURCES.md and supporting documentation with citations
   and an explicit GO/BLOCKED checklist for subsequent build issues.

Perform safe static checks. Do not access the user's handheld, change
firmware, download Pokémon fangames, package copyrighted game assets,
modify unrelated files or start Issue #4.

Open a focused PR linked to #3 and leave it unmerged. Include actual
commands/evidence, sources, test results, unresolved obligations and
the precise next unblocked step.
```

**Done:** M0 provenance matrix exists and is reviewable; no claim of legal clearance without documented evidence.
