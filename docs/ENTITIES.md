# Entitäten und Capability-Regeln

Eine Capability wird nicht aus einem Modelltemplate erzeugt, sondern aus
einer gelesenen Ressource. Schreibbarkeit braucht bekannte Payload-Semantik
und, wo vorhanden, eine vom Gerät gemeldete Optionsliste.

| Key | Plattform | Quelle | Schreiben |
|---|---|---|---|
| `machine_state` | sensor | operational state | nein |
| `cycle_active` | binary_sensor | Zustand + Fortschritt | nein |
| `program_progress` / `%` | sensor | operational state | nein |
| `remaining_time` / `estimated_finish` | sensor | Gerätrestzeit | nein |
| `program` | select | Course + echte Kursliste | ja, mit Smart Control |
| `temperature`, `spin_speed`, `rinse_count` | select | Washer-Wert/-Optionsliste | nur mit Optionsliste |
| `start`, `pause`, `stop` | button | operational state | echte Protokollwrites |
| `remote_control_enabled`, `child_lock` | binary_sensor | OCF/vendor resources | nein |
| `energy_consumption`, `power_consumption` | sensor | lokaler Zähler | nein |
| `media_player`, `remote` | TV | Tizen WS/REST | ja |
| `application` | select | erkannte/manuell konfigurierte/bestätigte App | ja |

Programmwerte können rohe Gerätecodes wie `1C` sein. Ohne gesicherte,
tabellenspezifische Übersetzung ist der rohe Code ehrlicher als ein erfundener
Programmname.

Alle Unique IDs sind `<stable-device-id>_<capability-key>`. Wenn eine Firmware
eine Capability entfernt, wird ihre bestehende Entität unverfügbar. Wenn sie
eine hinzufügt, kann die geladene Plattform sie ergänzen; unbekannte Ressourcen
erzeugen einen Repair, aber keine generische Schreibentität.

Der TV-`media_player` bietet `turn_on` nur mit gültig konfiguriertem
Wake-on-LAN an. Erkannte oder manuell konfigurierte Apps erscheinen neben
HDMI-Quellen in `source_list`; Namenskollisionen erhalten ein `App:`-Präfix.
`media_player.play_media` akzeptiert `media_content_type: app`. Alle drei Wege
(`select_source`, `play_media`, `samsung_local.launch_app`) verwenden denselben
internen Launcher und erfinden keine aktive Quelle, wenn der TV sie nicht
zurückmeldet.
