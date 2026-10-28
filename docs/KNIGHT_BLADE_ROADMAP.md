# Knight Blade: first playable RPG Maker XP game

**Current progress: 70% — static ABI and device loader pass; engine start pending.**

Updated: 2026-10-28. Source of truth:
[`knight-blade-progress.json`](../build/h700-engine/knight-blade-progress.json).
Weights measure completed milestones, **not elapsed time, probability of
success or remaining effort**. Failed verification reopens a milestone and
reduces progress. Hard blockers can still exist at 99%.

## Checklist

| Done | Weight | Milestone |
| --- | ---: | --- |
| Yes | 15% | Toolchain, sysroot, device access and measured baseline |
| Yes | 5% | Stock Ruby/extension trial on H700; engine Ruby still untested |
| Yes | 10% | Engine sources and selected dependency inputs pinned |
| Yes | 5% | Offline cross configuration |
| Yes | 30% | Dependencies, patched Ruby and engine compiled and linked |
| Yes | 5% | Remove build RPATH; audit architecture, interpreter and exact symbol/version/provider closure |
| No | 10% | Asset-free engine start, Ruby binding and visible GLES rendering on H700 |
| No | 5% | Audio, controls, bounded exit and clean NextUI return |
| No | 3% | Inventory owner-provided Knight Blade version/files and RTP requirements |
| No | 5% | Title screen, new game, first playable map |
| No | 5% | Movement, dialogue, representative battle/event, music/effects |
| No | 2% | Save/load, repeated cold start, safe exit and final evidence |

## What 100% means

Knight Blade is actually playable on **RG35XX Pro + NextUI**, not merely
linked or showing a title screen. Record game version, firmware, engine hash,
sanitized logs and the checks above. A representative gameplay session must
have no blocking defect; a complete playthrough is not required.
Public release, clean-room reproduction and other games are separate goals.
No game assets or RTP may be committed or distributed here.

## Evidence and next action

- [Engine build evidence](../build/h700-engine/engine-build-evidence.json):
  `MESON_COMPILE_PASS`, 684/684 steps, 463 seconds, 34,914,232-byte AArch64
  candidate. No target-execution attempts found in logs. **Host evidence only.**
- Readelf found `/job/sdl-prefix/lib:$ORIGIN` in the build candidate. The
  upstream `meson install --no-rebuild --destdir /job/staged --tags mkxp-z`
  correctly changes this to `$ORIGIN` in a private staging directory. Staged
  engine hash: `33b15913859596645d4051bed403e6f0e0953e6d8366db3b06665a9a96ce73f3`.
  No system installation/device transfer occurred. **Next:** audit that staged
  executable against exact device providers; this static milestone now passes.
- [Final static ABI audit](H700_ENGINE_ABI.md): 926 strong imports across ten
  objects, including actual device SDL, samplerate and libgcc. Both COPY
  relocation sizes match. The narrow opt-in `$ORIGIN` policy does not permit
  arbitrary RPATH/COPY bypasses. This does **not** prove runtime binding.
- Device access restored: [loader-only test](H700_ENGINE_ABI.md) now PASS
  (`--verify` and `--list`, both exit 0; provider hashes matched before/after).
  Engine was transferred to a private `/tmp` stage but **not started**.
  **Next:** [asset-free engine smoke](H700_ENGINE_SMOKE.md); visible output needs
  human confirmation. The v2 payload is now fully hash-verified on device and
  our Tools launcher updated. Exit Pak Store normally, then manually launch
  **Tools → MKXP Engine Smoke** and report image/sound/buttons/menu return.
  Preparation/staging does not complete a hardware milestone.
- The local OpenAL Soft GCC 8 patch and the SDL pkg-config sysroot correction
  are necessary build fixes; successful setup alone did not detect them.

## Autonomy and escalation

Continue with the first unfinished milestone, reuse successful artifacts where
possible, run relevant checks and update JSON, this percentage, evidence and PR
together. Every progress report states the percentage. Never complete hardware
milestones from host/CI tests. Work autonomously on routine build/code/debugging.
Report missing access, legal files, physical observations or required explicit
authorization. Do not lower limits further or deploy firmware to bypass blockers.

### Still needed from the owner

1. **Knight Blade:** legally obtained game directory, exact version and a private
   accessible path. Specify RTP requirements and provide legally obtained RTP
   if needed. Never upload game/RTP files to Git or publicly. No automated
   game/RTP download is planned. This does not block the asset-free smoke test.
2. **Physical observations:** if remote logs cannot prove visible output, speaker
   sound or physical controls, a short human on-device checklist is needed.
   SSH execution alone cannot prove these observations.

Selected dependency/embedded-asset rights review remains open, especially before
distribution. A private build does not clear that gate.

### Approved build limits

Owner approved a **5 GiB hard disk reserve** on 2026-10-28. Stop at **6 GiB
free** (1 GiB headroom); fresh setup starts at **7 GiB** or more. Keep 2 CPUs /
4 GiB, network-less unprivileged containers. No unrelated cleanup is authorized.
