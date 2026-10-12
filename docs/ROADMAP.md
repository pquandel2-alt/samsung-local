# Roadmap

## Vor erster Beta-Veröffentlichung

- reale Tests der drei Zielgeräte und redigierte Diagnosen;
- erneuter Config-Flow-/Entity-Test gegen HA 2026.9+, sobald das Testplugin
  diesen Core-Stand bindet (Python-3.14-/HA-2026.6.2-Lauf ist erfolgreich);
- HACS- und Hassfest-Ergebnis im veröffentlichten GitHub-Repository;
- automatische Legacy-Tokenausgabe nur nach sicherem Callback-Design.

## Nach Hardwarebefund

- WW90T554AAE/S2-spezifische, aber capability-basierte Feldlücken schließen;
- lokalen Samsung IP Control als optionalen TV-Unteradapter untersuchen;
- Bild-/Tonmodus nur bei bestätigter les-/schreibbarer lokaler API;
- verschlüsselte PIN-API für ältere Tizen-Generationen;
- zusätzliche Appliance-Mappings für Trockner, Geschirrspüler, Kühlschrank,
  Klimaanlage und Luftreiniger;
- echte Finish-Time-Hysterese und weitere tabellensichere Programmnamen.

## Stable-Gate

Kein Stable-Release vor positiven Hardware-, Offline-, Reconnect- und
Sicherheitsprüfungen. Ein bestandener Mock-Test ändert nie einen Matrixeintrag
auf `confirmed`.
