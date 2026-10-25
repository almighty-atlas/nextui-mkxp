# Issue-by-issue Codex workflow

One Codex job per GitHub issue. Start with the first unblocked M0 issue, then follow issue dependencies and roadmap gates. Never assign concurrent jobs that edit the same files or share a hardware-only resource without coordination.

## Reusable Codex prompt

```text
Repository: almighty-atlas/nextui-mkxp
Task: implement GitHub Issue #<NUMBER> ONLY.

First read AGENTS.md, README.md, docs/ROADMAP.md,
docs/ARCHITECTURE.md, docs/TEST_PLAN.md, and the full issue.
Inspect current main and existing PRs so the task is not duplicated.

Use a dedicated branch from current main. Execute the issue's
acceptance criteria, avoiding unrelated changes. Pin all upstream
source revisions and document provenance. Do not use game files,
modify firmware/system partitions, change root privileges, or assume
the ARM32 R36S binary runs on H700.

Run safe static/host tests where available. For hardware checks,
provide a precise read-only test script or manual checklist and
clearly mark H700 items NOT_TESTED until an actual device test.
If blocked, document the evidence and submit the smallest useful PR
instead of reporting fictional success.

Open a PR (do not merge) linking the issue, with summary, files,
commands/results, verified-vs-unverified matrix, risks and follow-ups.
Never mark an issue complete without its test evidence.
```

## Review gate

Check scope, licensing/provenance, tests, compatibility claims, rollback, file paths, and secrets. Merge only when the user's review criteria have been met. After merge, pick the next dependency-unblocked issue and substitute its number in the prompt.
