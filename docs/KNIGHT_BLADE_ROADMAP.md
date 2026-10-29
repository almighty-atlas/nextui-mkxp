# Knight Blade: first playable RPG Maker XP game

**Current progress: 100% — Knight Blade is playable on H700 (private test stage, owner-verified).**

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
| Yes | 10% | Asset-free engine start, Ruby binding and visible GLES rendering on H700 |
| Yes | 5% | Audio, controls, bounded exit and clean NextUI return |
| Yes | 3% | Inventory owner-provided Knight Blade version/files and RTP requirements |
| Yes | 5% | Title screen, new game, first playable map |
| Yes | 5% | Movement, dialogue, representative battle/event, music/effects |
| Yes | 2% | Save/load, repeated cold start, safe exit and final evidence |

## What 100% means

Knight Blade is actually playable on **RG35XX Pro + NextUI**, not merely
linked or showing a title screen. Record game version, firmware, engine hash,
sanitized logs and the checks above. A representative gameplay session must
have no blocking defect; a complete playthrough is not required.
Public release, clean-room reproduction and other games are separate goals.
No game assets or RTP may be committed or distributed here.

## Evidence and next action

- 2026-10-29: [fresh engine rebuild](H700_ENGINE_REBUILD.md) reproduces the build
  and installed ELF plus all 844 private Pak runtime files byte-for-byte.
  Upstream gemspec dates differ; tool bootstrap/public-release gates stay open.
  This is host-only evidence and does not change the **100%** playability score.

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
  human confirmation. v2 produced four successful process traces, patched
  Ruby 3.1.3, Mali-G31/GLES 3.2 and owner-confirmed color bars/moving square.
  One frame-limit exit and three Cancel exits completed normally.
- Owner heard no v2 tone (volume 40 ≈ −21 dB, 200 ms). [v3](H700_ENGINE_SMOKE.md)
  (volume 85, 600 ms) is **audible**; the pink square follows D-pad and left
  stick; RGSS A/B/C/X/Y/Z/L/R events are logged; NextUI menu works normally
  after the automatic end. Lifecycle milestone done (verified-on-H700).
- Known input gaps for the Pak: mkxp-z's default controller table leaves
  Start, Select, Menu/Guide and L2/R2 unbound and uses Xbox positions, so RGSS
  names differ from Anbernic labels (physical A acted as Cancel). A Pak needs
  an explicit, documented mapping (physical A = Confirm, B = Cancel, Start =
  menu) plus a deliberate quit path; this belongs to game inputs / Pak work.
- [Inventory](KNIGHT_BLADE_INVENTORY.md) done (verified-on-host): owner-designated
  official game and RTP downloads, hash-recorded and kept private. 583
  references: 520 game, 62 RTP, 1 pre-existing gap; no Win32API. RTP and a
  MIDI soundfont (28 MIDI tracks) are required.
- [First game boot](KNIGHT_BLADE_BOOT.md) **PASS (verified-on-H700)**: owner saw
  the title screen, heard MIDI music and effects, started a new game, moved,
  fought, used the main menu and saved, with no restriction noticed. ~7 min run,
  in-game shutdown, exit 0, peak RSS ≈205 MB of 1 GB.
- Second run (fresh engine launch, no device reboot): Continue loaded `Save1`,
  dialogue, play, in-game shutdown, NextUI returned normally; exit 0 again.
- **100% reached.** Not covered: full playthrough, reboot between sessions,
  long-session thermals/battery, installable Pak. Next project goal: a real
  RMXP.pak (#8 launch discovery, #10 controls/exit, #11 save isolation).
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
