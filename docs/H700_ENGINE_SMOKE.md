# Asset-free engine smoke: prepared, final device staging blocked

2026-10-28 · Refs #7 · Stacked on PR #34 (the completed #6 loader result).
**Knight Blade: 70%. No engine-start/render/audio/input milestone is complete.**

The physical [loader-only test](H700_ENGINE_ABI.md) passed. This next test
actually enters mkxp-z and its patched Ruby. It is deliberately launched
**by the owner from NextUI Tools**, not via an unsolicited SSH command while
NextUI is drawing. No daemon is killed/restarted and no firmware is changed.

## Current staging / blocker — do not launch yet

- A first private v1 payload was hash-verified in `/tmp`, with a new
  `Tools/h700/MKXP Engine Smoke.pak/launch.sh` entry. Existing Tools/games
  were untouched. No v1 work directory existed at the last successful check.
- Source review then found that the engine's path cache is created before
  our script generates its tone. The final v2 config disables `pathCache`
  so this freshly generated file can be found; no engine patch is needed.
- v2 is packaged on tiny02, but the device disconnected again: SSH timeout,
  then `Host is unreachable`, **before** v2 directory creation or launcher
  replacement. The installed launcher still points at v1. **Do not use it.**
- Keep the device powered and awake with the authorized network/SSH available.
  No idle/standby or networking policy was changed to work around this.

The next agent action is to stage v2, validate all manifest entries, and
atomically replace **only our own** Tools launcher after checking its v1
hash and confirming no old test is active. Never overwrite an unrelated tool.
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
- `launch.sh`: the sole new SD file, pointing to the private `/tmp` v2 payload.

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

Final v2 archive: 14,359,358 bytes; 842 pure Ruby files; SHA-256
`266230d3194f30172230c7a170f5e0bd866f474b1f10cd9030a96288b8a086dd`.
Private receipt SHA-256:
`5640aa8426dbf1e6706d32df4678201d09fedbe1b3e34d5b009d072f51dc9ab9`.
[Evidence record](../build/h700-engine/engine-smoke-evidence.json).

Host verification: **135 unit tests PASS**, native Ruby 3.1.3 `-c` PASS,
Python compileall, shell syntax and diff checks. Tests use synthetic inputs,
not a graphics mock presented as hardware evidence. No CI/hardware smoke PASS.

## Human device checklist (German)

**Erst nach bestätigter v2-Übertragung starten.**

1. Gerät eingeschaltet und wach lassen, SSH aktiv. Falls nötig den Tools-Ordner
   neu öffnen; keine Dienste neu starten. Noch nicht starten, solange v1 aktiv ist.
2. In NextUI unter **Tools → MKXP Engine Smoke** auswählen. Das ist ein
   temporärer Test, kein Spiel und kein fertiges RMXP-Pak.
3. Erwartet: links nach rechts rote, grüne, blaue und gelbe Streifen, lesbarer
   Text, bewegtes weißes Quadrat; Orientierung und Seitenverhältnis korrekt?
4. Bei niedriger, hörbarer Gerätelautstärke auf zwei kurze Töne achten
   (etwa nach 1 und 10 Sekunden). Die Testskripte ändern die Lautstärke nicht.
5. D-Pad und Face-/Schultertasten einzeln drücken. Die tatsächliche physische
   Zuordnung wird erst aus Beobachtung + Log ermittelt, nicht vorausgesetzt.
   **RGSS-Cancel** beendet den Test; dadurch kann er schon vor Ton 2 enden.
6. Ohne Eingabe endet er regulär nach ungefähr 30 Sekunden (Watchdog spätestens
   nach rund 48 Sekunden). Gibt es einen Fehlerdialog, schwarz/falsch gedrehtes
   Bild oder einen Hänger? Nicht wiederholt blind starten; Zustand melden.
7. Kommt NextUI zurück? Navigation und Ton danach normal? Das gilt auch als
   notwendige Kontrolle nach einem abgebrochenen oder fehlgeschlagenen Test.
8. Kurz berichten: **Bild / Ton / gedrückte Tasten / Rückkehr**. Der Agent liest
   anschließend nur die privaten Testlogs und aktualisiert Evidenz/Roadmap.

No screenshot/video, game data or personal path is required in the public repo.
Logs stay in `/tmp/nextui-mkxp-engine-smoke-v2/work/run-*/run.log`; preserve
them before reboot. A fresh run never reuses another run's work/data directory.

## Cleanup after testing

Only the newly created `Tools/h700/MKXP Engine Smoke.pak/launch.sh` (and its
now-empty directory) and these exact private `/tmp` test stages are disposable.
Check their hashes/ownership and preserve evidence before removing them.
Do not remove anything in existing Tools, games, saves or `.system`.
