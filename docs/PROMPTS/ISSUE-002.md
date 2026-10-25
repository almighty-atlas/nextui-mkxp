# Codex task — GitHub Issue #2 (H700 NextUI mkxp architecture)

## Goal

Produce a **source-grounded architecture decision** for how native RPG Maker XP / mkxp-z will launch and render on the **RG35XX Pro H700 with Base OS 1.4.0 / NextUI-20261013-0**.

**Highest-priority question:** the owner's H700 probe found `/dev/fb0` but no accessible `/dev/dri/card*` or `renderD128`, while EGL/GLESv2 and bundled NextUI SDL2 exist. How can a standalone mkxp-z instance create an accelerated graphics surface on this device? Distinguish what can be proven from source from what requires a harmless on-device smoke test.

## Source evidence

- Issue [#1](https://github.com/almighty-atlas/nextui-mkxp/issues/1#issuecomment-6403001093) includes **owner-supplied, sanitized hardware metadata**. PR [#20](https://github.com/almighty-atlas/nextui-mkxp/pull/20) documents it in `docs/H700_BASELINE.md`, currently unmerged.
- [NextUI PAKS.md](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/PAKS.md) — standalone Pak contract, ROM folder tags, GL libretro limitation.
- [Pinned NextUI H700 launch script](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/MinUI.pak/launch.sh) — runner environment, SDL2 library paths, lifecycle.
- [Pinned NextUI H700 model mapping](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/bin/h700-device.sh).
- [R36S native reference port](https://github.com/Periko21/mkxp-z-r36s/tree/b665091c1ff571a7a468bbf33af2f7c803c75220): **ArkOS RK3326 / armhf**, KMS/DRM + GLES; this **does not establish H700 graphics compatibility**.
- [Experimental NextUI mkxpz](https://github.com/KrutzOtrem/nextui-mkxpz) release **v0.6.7**: package metadata lists **tg5040/tg5050 only**; self-described unstable; public repository currently provides README/pak.json rather than reproducible source/launcher. Use as a **research lead**, not as an approved dependency, binary to run, or H700 port.
- [PR #19](https://github.com/almighty-atlas/nextui-mkxp/pull/19) license inventory and STOP/GO gate, still unmerged. No blind import or redistributed engine binary.

## Codex instructions

```text
Repo: almighty-atlas/nextui-mkxp
GitHub issue: #2 [M0] Decide mkxp-z integration architecture and game discovery contract.

1. Read AGENTS.md, README.md, Issue #2 (including comments), Issue #1
   owner-provided inventory, PRs #19 and #20, and relevant M0 documentation.
   Inspect current main and any other concurrent work. Avoid modifying
   shared files touched by unmerged PRs unless explicitly coordinating a
   clean base/rebase strategy. Do not merge any PR without user approval.

2. Read *pinned source* for NextUI's H700 startup, SDL2 graphics backend,
   framebuffer/EGL integration, launcher environment and emulator Pak
   dispatch. Do not assume an available /dev/fb0 means accelerated GLES
   works. Investigate whether the shipped SDL2 supports a compatible
   EGL/GL surface and whether software framebuffer rendering is a useful
   fallback given RGSS performance requirements.

3. Compare THREE candidates with explicit evidence and tradeoffs:
   A. native standalone mkxp-z using H700-compatible SDL/EGL/GLES backend;
   B. mkxp-z libretro with an alternative OpenGL-capable frontend, noting
      NextUI MinArch does not implement GL libretro API;
   C. a PortMaster-derived route or the experimental NextUI mkxpz project
      for architecture only (tg5040/tg5050, not proven on H700).
   Also inspect the existing R36S ArkOS armhf port as a reference, not
   binary-compatible artifacts.

4. Prove from NextUI source (or record as UNKNOWN) its ROM file discovery
   and parent-folder tag convention, whether Game.ini, directory launchers
   or marker files can be selected, how arguments are quoted/escaped and
   how a standalone process returns to NextUI. Give the minimal reversible
   RMXP.pak layout and one-game/two-game per-user data model, including
   paths with spaces, missing files and safe exit.

5. Prepare an ADR (architecture decision record), supported by exact
   upstream commit+file/line refs, assumptions, a comparison matrix and
   a ONE-SMOKE-TEST proposal. The smoke test must be game-free and
   redistributable, avoid firmware/system changes and privileged
   operations, and test actual video context creation and clean return.
   Do not implement a complete engine or launch unknown third-party
   binaries in this issue.

6. Differentiate SOURCE_CONFIRMED, OWNER_OBSERVED_H700, HYPOTHESIS,
   and NOT_TESTED. If safe documentation work is possible while #1 PR #20
   is unmerged, make a documentation-only branch and PR referencing #2.
   Avoid conflicting changes to docs/ARCHITECTURE.md, docs/COMPATIBILITY.md
   and docs/TEST_PLAN.md touched by PR #20: if conflict is unavoidable,
   prepare the ADR as a new standalone docs/ADR-0001-*.md file and link it
   in PR description; postpone shared-file edits.

7. Run all applicable static/document checks. Open one unmerged PR with
   evidence, tradeoffs, gate status, blocker list and a suggested first
   harmless device smoke test. Do not mark #2 completed without either
   pinned source evidence establishing the Pak-discovery contract or an
   explicit unresolved gate. Never claim graphics works before hardware
   test. Do not perform a full engine build or start Issue #4.
```

## Definition of Done

- Concrete, source-grounded graphics strategy with an explicit feasibility gate.
- Clear Pak discovery, entrypoint, lifecycle and per-game data design.
- Risks/alternatives explained, all hardware assumptions tagged.
- No game assets, unlicensed binaries or system modifications.
- A clean unmerged PR or a documented blocker that avoids editing concurrent PR files.

## User action

No user commands are required for the *research-only* stage. Hardware testing
will be a separate, reviewed, small smoke test after the ADR is approved.
