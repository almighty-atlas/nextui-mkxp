# Asset-free engine smoke: v2 partial PASS, v3 staged

2026-10-28 · Refs #7 · Stacked on PR #34 (the completed #6 loader result).
**Knight Blade: 80%. Engine/Ruby and visible GLES rendering pass on H700;
audible sound, full controls and NextUI navigation after return remain open.**

The physical [loader-only test](H700_ENGINE_ABI.md) passed. This test
actually enters mkxp-z and its patched Ruby. It is deliberately launched
**by the owner from NextUI Tools**, not via an unsolicited SSH command while
NextUI is drawing. No daemon is killed/restarted and no firmware is changed.

## v2 result (verified-on-H700, owner-launched)

| Check | Result |
| --- | --- |
| Video | **PASS** — owner saw color bars and moving white square; logs: ARM Mali-G31, OpenGL ES 3.2 v1.r20p0-01rel0 |
| Ruby embedding | **PASS** — four traces report Ruby 3.1.3 aarch64-linux and `SMOKE_SCRIPT_PASS` |
| Exit | Four process exits 0 + `SMOKE_RUNNER_PASS` (one frame limit, three Cancel); owner reports automatic end after ~30 s |
| Input | RGSS events logged for DOWN/LEFT/RIGHT/UP, L, R, A, B, C, X; v2 only visibly reacted to Cancel (physical A) |
| Audio | **NOT_HEARD** — ALSA opened and SE playback requested without logged error; not a PASS |

[Sanitized log excerpts](evidence/2026-10-28-engine-smoke-v2.txt); raw log
hashes are in the [evidence record](../build/h700-engine/engine-smoke-evidence.json).

Audio hypothesis (source-grounded, not proven): mkxp-z maps RGSS volume onto
a −35 dB scale, so v2's volume 40 was about −21 dB on top of a 200 ms PCM
tone with peak 3000 (about −42 dBFS combined), before the device mixer.

## v3 — staged, awaiting manual test

v3 changes only `smoke.rb` and the launcher path: 600 ms tone, PCM peak 6000,
SE volume 85 (about −5.25 dB), Confirm replays the tone, a magenta square
moved by the D-pad, an on-screen label for every RGSS input, and Cancel must
be **held for one second** to exit. No mixer or system volume is changed.

All v3 manifest entries passed SHA-256 validation on the device; our own
Tools launcher was atomically replaced after checking the v2 launcher hash
(new hash `13cb699299e3009322c5d03e2a328429562bb07a62c4442ca07b02bb44e40418`,
pointing to `/tmp/nextui-mkxp-engine-smoke-v3`). No engine process and no v3
work directory existed at the final check.

## v2 staging (historical)

The owner restored access and kept the device awake in Pak Store. The v2
payload was staged with every manifest entry hash-verified and the nine
runtime-provider hashes, NextUI revision and kernel unchanged.

### Historical staging interruption

- A first private v1 payload was hash-verified in `/tmp`, with a new
  `Tools/h700/MKXP Engine Smoke.pak/launch.sh` entry. Existing Tools/games
  were untouched. No v1 work directory existed at the last successful check.
- Source review then found that the engine's path cache is created before
  our script generates its tone. The final v2 config disables `pathCache`
  so this freshly generated file can be found; no engine patch is needed.
- v2 is packaged on tiny02, but the device disconnected again: SSH timeout,
  then `Host is unreachable`, **before** v2 directory creation or launcher
  replacement. At that time the installed launcher still pointed at v1.
- Keep the device powered and awake with the authorized network/SSH available.
  No idle/standby or networking policy was changed to work around this.

Those final staging/launcher actions are now complete. Never overwrite an
unrelated tool on future retries.
If the device rebooted, `/tmp` payloads may have disappeared: re-stage using
fresh paths; do not assume their presence from the SD launcher alone.

## Fixture and provenance

`tests/hardware/engine-smoke/` contains original MIT-licensed scripts and config:

- `smoke.rb`: procedural RGB/yellow bars, embedded-engine fallback text and
  moving white square; quiet original 440 Hz PCM generated in the work dir;
  RGSS input event logging and Cancel exit. No external image/font/game/RTP.
- `mkxp.json`: RGSS1, 640×480, fullscreen, no RTP/preload/patches, no JIT,
  no reset/settings menu, no symlinks or path cache. The engine's existing
  embedded font remains subject to upstream license review; no font is added.
- `run.sh`: fresh per-run work/home/data directories, clean environment,
  measured NextUI library path, `LD_BIND_NOW=1`, Mali/GLES and ALSA (no null
  audio fallback). Existing device ALSA config/plugins are only read.
- `launch.sh`: the sole new SD file, pointing to the private `/tmp` v3 payload.

The launcher requires `IS_NEXT=yes`, `PLATFORM=h700` and the Tools argument,
and refuses if `nextui.elf` is still running. The observed firmware's
`MinUI.pak/launch.sh` runs selected Paks after `nextui.elf` exits and resumes
the normal menu loop afterwards. That system script was read, not copied or
modified. No guarantee of lifecycle success is made before the human test.

Resource bounds: 1,800 graphics updates (~30 seconds at 60 fps), outer process
timeout 45 seconds plus 3-second kill grace, core dumps disabled and per-file
write limit. A timeout is a failed/incomplete test, not clean teardown evidence.
The watchdog only controls the test process group, never system services.
`SMOKE_SCRIPT_PASS` is mandatory because mkxp-z can return process exit 0 on
initialization failure. Even that marker does not prove visible pixels or sound.

This uses the existing root SSH/NextUI account, **not** an unprivileged device
sandbox. The test deliberately changes the display/audio only when selected by
the user. No CPU governor, mixer volume, sysctl, partitions or global state is
modified by these scripts. Engine config/saves go only to the private work dir.

## Private packaging / reproducibility

```sh
python3 scripts/prepare_h700_engine_smoke.py \
  --engine-prefix "$PRIVATE_JOB/staged/usr/local" \
  --output "$FRESH_PRIVATE_PAYLOAD"
```

The helper requires the recorded static ABI and H700 loader PASS, verifies the
exact installed engine hash, copies only pure `.rb` stdlib files plus the
engine/license and our explicit fixture allowlist, writes SHA256SUMS and a
private archive/receipt. It never deploys or executes the engine. Downloaded
third-party sources and binaries remain outside Git; distribution is BLOCKED.

Tested v2 archive: 14,359,358 bytes; SHA-256
`266230d3194f30172230c7a170f5e0bd866f474b1f10cd9030a96288b8a086dd`.
Staged v3 archive: 14,359,819 bytes; 842 pure Ruby files; SHA-256
`4f6ec237d6a178d1b29bea2b509fb46d35f622250156030eda0c76186abfaeca`;
private receipt SHA-256
`490663d83579f67c78868ea128fc434701558eb0c74b02e75b73228eb3998196`.
[Evidence record](../build/h700-engine/engine-smoke-evidence.json).

Host verification: **136 unit tests PASS**, native Ruby 3.1.3 `-c` PASS,
Python compileall, shell syntax and diff checks. Tests use synthetic inputs,
not a graphics mock presented as hardware evidence. No CI/hardware smoke PASS.

## Human device checklist v3 (German)

1. Gerät eingeschaltet und wach lassen, SSH aktiv. Pak Store vorher regulär
   verlassen; keine Dienste neu starten.
2. Gerätelautstärke auf ein mittleres, angenehmes Niveau stellen.
3. **Tools → MKXP Engine Smoke** starten. Farbstreifen und weißes Quadrat wie
   bei v2 erwartet.
4. Auf Töne achten: nach ca. 1 und 10 Sekunden (je 0,6 s lang). Zusätzlich die
   Bestätigen-Taste drücken – jedes Drücken fordert den Ton erneut an.
5. Mit dem D-Pad das **pinke Quadrat** bewegen. Jede Taste einzeln drücken
   (A, B, X, Y, L1, R1, L2, R2, Select, Start) und notieren, welcher Text oben
   erscheint („RGSS input: …“). Kurzes Drücken von Cancel beendet nicht mehr.
6. Zum Beenden Cancel **eine Sekunde halten**, oder ca. 30 Sekunden warten.
7. Kommt NextUI zurück? Menü-Navigation und Menüton danach normal?
8. Kurz berichten: **Ton ja/nein, Quadrat folgt D-Pad, Tasten→Text, Rückkehr**.

No screenshot/video, game data or personal path is required in the public repo.
Logs stay in `/tmp/nextui-mkxp-engine-smoke-v3/work/run-*/run.log`; preserve
them before reboot. A fresh run never reuses another run's work/data directory.

## Cleanup after testing

Only the newly created `Tools/h700/MKXP Engine Smoke.pak/launch.sh` (and its
now-empty directory) and these exact private `/tmp` test stages are disposable.
Check their hashes/ownership and preserve evidence before removing them.
Do not remove anything in existing Tools, games, saves or `.system`.
