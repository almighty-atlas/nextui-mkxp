# A separate playable recovery check (#11)

`scripts/rmxp_recovery_check.py` prepares the final human load test without
replacing a live state. Run it on a preparation computer against a stopped
private state directory, or a complete byte copy from the device. Python is
not required on H700.

```sh
python3 scripts/rmxp_recovery_check.py \
  --state /private/card/.userdata/h700/nextui-mkxp/<ID> \
  --workspace /private/fresh-recovery-round
```

The workspace must be fresh, outside the source repository/state and have space
for four copies plus 32 MiB. A failure leaves evidence in that owned workspace;
the helper does not delete it or change original saves. Outputs contain private
game data and must never be attached, committed or distributed.

1. Snapshot the complete state and verify it with the existing SHA-256 tool.
2. Restore into `restored-sd/` and require a bit-identical inventory of all state
   files. This is the actual non-rebased restore result.
3. Copy the restored game into `out-sd/Games/Knight Blade Recovery/` and register
   it with a new stable game ID. Original IDs cannot be reused by this helper.
4. Rebase only the test registration's generated game/config paths. Copy the
   optional private pause script/session settings. The bit-exact restored tree
   remains unchanged; arbitrary old config/custom script paths are not migrated.
5. Require unchanged original files and exact restored game bytes. Return
   `hardware_load=NOT_TESTED`: a prepared save is not a successful load test.

Transfer **only `out-sd/` contents** to fresh destinations on the device. Never
extract over an existing source, marker or state ID. Use the already-reviewed
engine/RTP; this tool does not build or install another runtime. Preserve all
other private output trees as evidence until the test is accepted.

## Prepared round (2026-10-29)

Actual device-state copy, three saves: snapshot and full restore are identical.
The separate Recovery entry was installed using new paths only; all three
device save copies compare equal to the original. Original saves remained
unchanged. No game was remotely started or display ownership taken.

To avoid repeating the long introduction, the second instance ("Zwei's Ä") was
seeded with a copy of the original Save1 **only because no Save1 existed there**.
This seed is not claimed as independent saving; the human test below still
needs to write a different state.

Five host tests PASS: byte-exact full restoration and new config/ID binding,
no-overwrite/ID collision, locks/read-only saves, unsafe names/space exhaustion,
Unicode paths and no inherited custom-script paths. Device save comparison is
verified-on-H700 file evidence; the following visual test remains untested.

## Letzte Geräteschritte (deutsch)

1. **Knight Blade Recovery** starten und Speicherplatz 3 laden. Ist es derselbe
   Fortschritt wie im normalen Knight Blade? Über Quit wieder beenden.
2. **Knight Blade Zwei's Ä** starten, Speicherplatz 1 laden (Einleitung entfällt).
   Einige Schritte gehen und auf **Speicherplatz 4** speichern. Beenden.
3. Im normalen **Knight Blade** prüfen: Die Plätze 1–3 sind unverändert, der
   neue Platz 4 aus "Zwei's Ä" darf dort **nicht** erscheinen.
4. "Zwei's Ä" erneut starten und Platz 4 laden. Fortschritt korrekt?
5. Gerät regulär über NextUI neu starten; beide zuletzt geprüften Speicherplätze
   erneut laden. FAIL/BLOCKED statt PASS melden, wenn die Beobachtung fehlt.

Erst dann können D4/D6 und der D8-In-Game-Teil abgenommen werden. Das sind zwei
Instanzen desselben legalen Spiels, **kein** Nachweis für ein zweites Spiel oder
Pokémon Essentials.
