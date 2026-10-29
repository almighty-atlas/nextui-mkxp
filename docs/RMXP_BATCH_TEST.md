# Gemeinsame RMXP-Gerätetestrunde

Status: **vorbereitet, nicht ausgeführt**. Das Gerät ist derzeit nicht verfügbar.
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
| Gerät | RG35XX Pro / konkrete Variante |
| Firmware | genaue NextUI-Version |
| Pak-Commit / Engine-SHA256 | noch einzutragen |
| Testspiele / private Versionen | lokal festhalten |
| Datum / Beobachter | noch einzutragen |

## Ablauf mit erwartetem Ergebnis

| ID | Aktion | Erwartung | Status |
| --- | --- | --- | --- |
| D1 | NextUI öffnen | „RPG Maker XP“ und beide Einträge sichtbar | NOT_TESTED |
| D2 | Beide Spiele nacheinander starten | Richtiger Titel, Bild und Ton | NOT_TESTED |
| D3 | D-Pad/Stick, A/B, Start und verwendete Schultertasten prüfen | Bekannte Belegung; keine dauerhaft blockierten Tasten | NOT_TESTED |
| D4 | In beiden Spielen unterschiedliche Spielstände anlegen | Getrennte Dateien in den jeweiligen IDs | NOT_TESTED |
| D5 | Über Spielmenü beenden | Ton endet, NextUI bedienbar, Engine beendet, Lock entfernt | NOT_TESTED |
| D6 | Beide erneut starten und laden | Jeweils richtiger Fortschritt; Originalspiele unverändert | NOT_TESTED |
| D7 | Bei beendetem Spiel privaten Snapshot erstellen und verifizieren | Prüfsummen passen; Spielfunktion danach unverändert | NOT_TESTED |
| D8 | Snapshot auf frischem Test-SD-Verzeichnis wiederherstellen | Inhalte gleich; vorhandener Zustand wird bei Wiederholungsversuch abgewiesen | NOT_TESTED |
| D9 | Entbehrliche Testkopie mit fehlender Game.ini starten | Kurze Meldung, normale Rückkehr, keine veränderten Saves | NOT_TESTED |
| D10 | Diagnoseexport nach Erfolg und Testfehler erzeugen | Korrekte Statuskategorie; keine privaten Rohdaten im JSON | NOT_TESTED |
| D11 | Nur Pak/Engine durch geprüfte Folgeversion ersetzen | Spiel-IDs, Konfiguration und Saves erhalten | NOT_TESTED |
| D12 | Nach Abschluss und Sicherung Gerät regulär neu starten, erneut laden | Dauerhaftes SD-Pak vorhanden, richtiger Spielstand | NOT_TESTED |
| D13 | Geprüften AArch64-Supervisor zunächst ohne Eingabekonfiguration starten | Loader funktioniert; reguläres Beenden und NextUI-Rückkehr unverändert | NOT_TESTED |
| D14 | Event-Gerät und Start/Select-Codes passiv prüfen, dann session.conf setzen | Richtige Codes, keine exklusiv belegten Tasten | NOT_TESTED |
| D15 | Kurze Kombination, Start mit bereits gehaltenen Tasten und längeres Halten testen | Kurze/anfängliche Betätigung beendet nicht; 1,5 s Halten beendet nach Loslassen/erneutem Drücken | NOT_TESTED |
| D16 | TERM-ignorierende entbehrliche Testanwendung beenden | Fallback nach 3 s, keine fremden Prozesse betroffen, NextUI wieder bedienbar | NOT_TESTED |

Für D8 ist ein Spielstart nur möglich, wenn Originalquelle, Marker, Engine und
ggf. RTP/Soundfont im gleichen Gerätepfad bereitstehen. Nicht allein einen
Dateivergleich als erfolgreichen In-Game-Ladetest melden.

Die optionale Beenden-Kombination und der Prozesswächter aus
[#42](https://github.com/almighty-atlas/nextui-mkxp/pull/42) sind host-getestet und
für AArch64 gebaut; reale Codes und Audio/Display-Aufräumung sind noch offen.
Keine automatische Reparatur unterbrochener Saves oder Wiederherstellung nach
hartem Stromverlust behaupten. Kein unangekündigtes Ausschalten während eines Speicherns.

## Rückmeldung

Für D1–D16 jeweils PASS/FAIL/BLOCKED mit kurzer Beobachtung dokumentieren.
Firmware, Commits und Export-JSON beilegen; private Logs und Backups bleiben
lokal. Bei einem Fehler zuerst Daten erhalten, dann die Ursache untersuchen.
