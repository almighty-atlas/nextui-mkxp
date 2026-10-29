# First H700 fangame session (#52)

Device reconnected on 2026-10-29: RG35XX Pro, AArch64, NextUI-20261013-0
(`39a06de`). The installed engine and supervisor match the previously reviewed
SHA-256 values. Runtime manifest verification passed. Only NextUI was running,
not another engine. The ANBERNIC controller is still `event1`; the native
supervisor accepted the previously observed Select=310 / Start=311 codes.
No firmware/service restart, input grab or system-library replacement occurred.

## Candidate installation

The Sage and Rocket private candidates use **new** source folders, per-game IDs
and markers. Neither Knight Blade nor its shared engine/configuration is being
replaced. A pre-transfer checksum baseline covers existing saves.

An initial Sage transfer exceeded its command deadline. No marker was yet
present, so it was not advertised as a complete game. The resume procedure
verified 1,369 files and selected only 47 missing/nonmatching files (78,713,770
bytes). Matching files were not resent; no incomplete tree or save was deleted.
Final installation is accepted only after the full source/staging manifests
verify on the device.

**Completed:** all **1,416 Sage** and **2,014 Rocket** file checksums pass.
The seven pre-existing save-file checksums and shared runtime manifest also pass
unchanged after the transfer. Both new configs point to their own private copies,
have no preload overlay, and have their verified 310/311 session configuration.
Neither new game had a lock/running engine at the final check. Exact identities
and boundaries: [device staging evidence](../build/h700-engine/fangame-device-stage.json).

The normal launcher still requires a NextUI handoff and refuses to compete
with the menu for the display. No game is remotely started as part of copying
or checking files. A successful copy/hash check does not prove title rendering,
sound, controls or gameplay. Those remain **NOT_TESTED** until observed.

The standard Knight Blade pause overlay is disabled in both candidate configs.
Use the game's own menu; the native Select+Start hold remains an independent
escape path while game-specific menu/save adapters are being assessed.

## Erste Prüfung durch den Besitzer

Bitte zunächst **nur Pokemon Sage**, danach **Pokemon Team Rocket** auswählen.
Falls neue Einträge noch nicht sichtbar sind, einmal aus dem RPG-Maker-Ordner
zurückgehen und ihn erneut öffnen. NextUI nicht während eines laufenden Spiels
per SSH neu starten oder beenden.

Für jedes Spiel kurz notieren:

1. Erscheint ein Titelbild, eine Fehlermeldung oder nur ein schwarzer Bildschirm?
   Bei Fehlern reichen Meldung/Foto und der Spielname; Logs werden separat geprüft.
2. Ist Musik hörbar? Reagiert Bestätigen mit A und Zurück mit B?
3. Wenn ein neues Spiel möglich ist: bis zur ersten frei steuerbaren Karte gehen.
   Speichern/Laden und Kampf sind spätere Prüfpunkte, nicht aus einem Titelbild
   als bestanden ableiten.
4. Über das Spielmenü beenden, falls möglich. Sonst **Select+Start mindestens
   zwei Sekunden halten**. Danach müssen NextUI wieder bedienbar und der Ton aus
   sein. Kein hartes Ausschalten während eines Schreibvorgangs.

Nach dem ersten Fehler nicht weitere Kopien/Installer starten und keine Saves
löschen. Erst den tatsächlichen Fehler untersuchen. Insbesondere Windows-/Flash-
oder GIF-Verweise in der statischen Analyse begründen noch keinen pauschalen
Patch; sie können optionale oder bedingte Pfade sein.

## Reborn

Reborn wird in dieser ersten Runde noch nicht freigeschaltet. Die Spielscripte
verwenden unter anderem eigene D/E/F-Eingaben; die native Referenz bindet diese
nicht wie das mitgelieferte Spiel-Backend. Einfaches Aliasieren auf ALT/CTRL wäre
keine sichere Lösung, weil Reborn diese vorhandenen Tasten ebenfalls nutzt.
Auflösung, weitere API-/Ruby-Wrapper und Speicherformat sind separat zu prüfen.
Das gilt zusätzlich zum dokumentierten RAM-Risiko, nicht als Ersatz für einen
echten Test. Windows-EXE/DLLs werden nicht auf dem H700 ausgeführt.

Knight Blade's private playability remains **100%**. No new game's playability
is inferred from that milestone or from a process returning exit code zero.
