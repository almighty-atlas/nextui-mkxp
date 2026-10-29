# Gemeinsame RMXP-Gerätetestrunde

Status: **teilweise ausgeführt am 2026-10-29** (verified-on-H700 wo angegeben).
Ziel: Pak-Kandidat #40 und Offline-Werkzeuge für #11 in einer Sitzung prüfen.
Knight Blades bereits bestätigte private Spielbarkeit bleibt bei **100 %**
([#39](https://github.com/almighty-atlas/nextui-mkxp/pull/39)); dieser Wert gilt
nicht als Abnahme der neuen Pak- und Wiederherstellungsfunktionen.

## Vorbereitung am Rechner

- Verwendete Commits von #40 und dem State-Tools-PR notieren; Host-Tests ausführen.
- Zwei rechtmäßig vorhandene Spiele vorbereiten. Für denselben Spielinhalt in
  zwei Verzeichnissen nur „getrennte Instanzen“ bestätigen, keine zweite
  Spielkompatibilität behaupten. Ein Name enthält Leerzeichen, Umlaut und Apostroph.
- Bestehende Spielstände sichern. Für Fehlerfälle ausschließlich entbehrliche
  Testkopien nutzen. Keine echten Saves absichtlich beschädigen.
- Private Engine, RTP und Soundfont bereithalten. Keine Assets hochladen.
- Pak installieren und beide Einträge registrieren. Ausgangsprüfsummen der
  Originalspiele und der beiden privaten Spielstände festhalten.

## Gerätedaten

| Feld | Eintrag beim Test |
| --- | --- |
| Gerät | RG35XX Pro, Kernel 4.9.170 aarch64 |
| Firmware | NextUI-20261013-0 (39a06de) |
| Pak-Commit / Engine-SHA256 | #40 6eaeac4, dann b7dcb8f / 33b15913…73f3; Supervisor 3e1aa386…396d |
| Testspiele / private Versionen | Knight Blade (privat, Besitzer), zwei Instanzen + entbehrliche Fehlerkopie |
| Datum / Beobachter | 2026-10-29 / Besitzer (Bildschirm, Ton, Tasten), Agent per SSH (Dateien, Logs) |

## Ablauf mit erwartetem Ergebnis

| ID | Aktion | Erwartung | Status |
| --- | --- | --- | --- |
| D1 | NextUI öffnen | „RPG Maker XP“ und beide Einträge sichtbar | PASS – Ordner mit drei Einträgen sichtbar |
| D2 | Beide Spiele nacheinander starten | Richtiger Titel, Bild und Ton | PASS (nach Fix b7dcb8f) – mit 6eaeac4 FAIL: Engine las mkxp.json nicht (fehlendes SRCDIR), Exit 0 sofort |
| D3 | D-Pad/Stick, A/B, Start und verwendete Schultertasten prüfen | Bekannte Belegung; keine dauerhaft blockierten Tasten | PASS – Bild, Ton, Tasten laut Besitzer korrekt (Knight Blade) |
| D4 | In beiden Spielen unterschiedliche Spielstände anlegen | Getrennte Dateien in den jeweiligen IDs | PARTIAL – Knight Blade schrieb Save2 nur in die private Kopie; zweite Instanz noch ohne Spielstand |
| D5 | Über Spielmenü beenden | Ton endet, NextUI bedienbar, Engine beendet, Lock entfernt | PASS – Rückkehr zu NextUI, Ton aus, Lock entfernt, RMXP_EXIT=0 |
| D6 | Beide erneut starten und laden | Jeweils richtiger Fortschritt; Originalspiele unverändert | PARTIAL – Knight Blade lädt Save1 und Save2; Original Games/…/Save1 unverändert; zweite Instanz offen |
| D7 | Bei beendetem Spiel privaten Snapshot erstellen und verifizieren | Prüfsummen passen; Spielfunktion danach unverändert | PASS (Host-Werkzeug auf Byte-Kopie vom Gerät) – 765 Dateien, SNAPSHOT/BACKUP_VERIFIED |
| D8 | Snapshot auf frischem Test-SD-Verzeichnis wiederherstellen | Inhalte gleich; vorhandener Zustand wird bei Wiederholungsversuch abgewiesen | PASS (Dateiebene) – RESTORE_VERIFIED bitgleich, Wiederholung EXISTING_STATE_PRESERVED; kein In-Game-Ladetest |
| D9 | Entbehrliche Testkopie mit fehlender Game.ini starten | Kurze Meldung, normale Rückkehr, keine veränderten Saves | PASS – Meldung „RMXP: Game.ini missing“, Rückkehr zu NextUI, kein Log/Save verändert |
| D10 | Diagnoseexport nach Erfolg und Testfehler erzeugen | Korrekte Statuskategorie; keine privaten Rohdaten im JSON | PASS – returned_zero/natural, returned_zero/chord, no_log; nur Kategorie missing_font |
| D11 | Nur Pak/Engine durch geprüfte Folgeversion ersetzen | Spiel-IDs, Konfiguration und Saves erhalten | PASS – Pak 6eaeac4 nach RMXP-rollback/ verschoben, b7dcb8f installiert; 847/847 Prüfsummen, Saves/IDs/session.conf unverändert |
| D12 | Nach Abschluss und Sicherung Gerät regulär neu starten, erneut laden | Dauerhaftes SD-Pak vorhanden, richtiger Spielstand | PASS – nach regulärem Neustart Pak vorhanden, Knight Blade startet und lädt |
| D13 | Geprüften AArch64-Supervisor zunächst ohne Eingabekonfiguration starten | Loader funktioniert; reguläres Beenden und NextUI-Rückkehr unverändert | PASS – Supervisor lädt auf H700; exit 0/143, Signal 15, exec 127 korrekt; NextUI-Rückkehr unverändert |
| D14 | Event-Gerät und Start/Select-Codes passiv prüfen, dann session.conf setzen | Richtige Codes, keine exklusiv belegten Tasten | PASS – passive Aufzeichnung event1 „ANBERNIC-keys“: Select=310, Start=311 (Menü=312, L2/R2=314/315); Annahme 314/315 war falsch und löste harmlos nichts aus |
| D15 | Kurze Kombination, Start mit bereits gehaltenen Tasten und längeres Halten testen | Kurze/anfängliche Betätigung beendet nicht; 1,5 s Halten beendet nach Loslassen/erneutem Drücken | PASS – kurzes Antippen beendet nicht; 2 s Halten beendet (REASON=chord, Exit 0), Rückkehr zu NextUI |
| D16 | TERM-ignorierende entbehrliche Testanwendung beenden | Fallback nach 3 s, keine fremden Prozesse betroffen, NextUI wieder bedienbar | PASS (Testprozess per SSH) – TERM ignoriert, KILL nach 3,14 s, fremder Prozess unberührt |

Für D8 ist ein Spielstart nur möglich, wenn Originalquelle, Marker, Engine und
ggf. RTP/Soundfont im gleichen Gerätepfad bereitstehen. Nicht allein einen
Dateivergleich als erfolgreichen In-Game-Ladetest melden.

Die optionale Beenden-Kombination und der Prozesswächter aus
[#42](https://github.com/almighty-atlas/nextui-mkxp/pull/42) sind host-getestet und
für AArch64 gebaut; reale Codes und Audio/Display-Aufräumung sind noch offen.
Keine automatische Reparatur unterbrochener Saves oder Wiederherstellung nach
hartem Stromverlust behaupten. Kein unangekündigtes Ausschalten während eines Speicherns.

## Rückmeldung

Für die letzte offene Runde steht nun ein [separater Recovery-Eintrag](RMXP_RECOVERY_CHECK.md)
bereit. Er prüft Wiederherstellen ohne Überschreiben und erspart mit einer
ausdrücklich als Kopie gekennzeichneten Save1-Saat die zweite Einleitung.
Die visuellen D4/D6/D8-Prüfungen bleiben bis zur Rückmeldung offen.

Offen: getrennte Spielstände zweier Instanzen (D4/D6) und In-Game-Laden eines wiederhergestellten Stands (D8).

Für D1–D16 jeweils PASS/FAIL/BLOCKED mit kurzer Beobachtung dokumentieren.
Firmware, Commits und Export-JSON beilegen; private Logs und Backups bleiben
lokal. Bei einem Fehler zuerst Daten erhalten, dann die Ursache untersuchen.
