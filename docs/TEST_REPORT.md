# Testbericht 0.1.0-beta.5

Datum: 14. Oktober 2026

## Ausgeführt

| Prüfung | Ergebnis |
|---|---|
| `python -m compileall` | erfolgreich |
| `ruff check custom_components tests` | erfolgreich |
| `mypy custom_components/samsung_local` (strict) | erfolgreich, 41 Dateien |
| `pytest -q` (Python 3.14.2 + echte HA-Harness) | 72 erfolgreich, 0 fehlgeschlagen |
| Coverage | 73 % gesamt; Apps 92 %, Power 96 %, Services 90 %, Connection Manager 90 % |
| `pip-audit --local` im Runtime-/Unit-Test-Satz | keine bekannten Schwachstellen |
| JSON-Parsing Manifest/Strings/Übersetzungen | erfolgreich |

Die 72 Tests umfassen Capability-Mapping, Phantom-Unterdrückung,
Firmware-Add/Remove, Zertifikats-/PSK-/Tokenvalidierung,
Completion-Deduplizierung, Reconnect-Backoff, WLAN-Ausfall,
Befehlssynchronisierung, WAN-blockierte Kernlogik, TV-Profilgrundsätze,
Config-/Options-/Reconfigure-Flows, reales HA-Setup/Unload, Entity Registry und
verschachtelte Diagnose-Redaktion. SSDP-Mehrfachantworten und der
Standby-Pairingfehler, fehlende Laufzeit-Tokens und unerwartete Tokenwechsel
besitzen eigene Regressionstests.

Neu geprüft wurden MAC-/Broadcast-/Port-/Timeout-Validierung, erfolgreicher
und fehlgeschlagener Magic-Packet-Versand, tatsächliche Bereitschaftsprüfung,
App-Aliase und Mehrdeutigkeit, gerätespezifische IDs, unbekannte Apps,
DEEP_LINK-Pfad, automatisches Wake-up, nicht verifizierbarer Aktivstatus,
Source-/Select-Pfad, serialisierte und überholte App-Aufträge, Options Flow,
Aktionsregistrierung/-entfernung, gültige und ungültige HA-Targets sowie ein
HA-Neustart mit bereits gekoppeltem WOL-TV im nicht erreichbaren Deep Standby.

## Testumgebungen und Repository-Validatoren

Die Kernsuite lief zusätzlich auf dem vorhandenen Python 3.12.3 (57 Tests
erfolgreich, 4 HA-Harness-Module erwartungsgemäß übersprungen).
Für die Integrationstests wurde CPython 3.14.2 installiert. Die aktuell
verfügbare `pytest-homeassistant-custom-component==0.13.338` bindet
Home Assistant 2026.6.2; der aktuelle HA-Core-API-Stand wurde zusätzlich im
Quellcode untersucht, aber nicht als ausgeführter 2026.9-Lauf ausgegeben.

Der GitHub-CI-Lauf für den Release-Stand muss vor Veröffentlichung erfolgreich
sein: Quality, Home-Assistant-Integrationstests, Hassfest und HACS validation.
Der separate Dependency-Security-Lauf wird bei geänderten Abhängigkeiten oder
Manifesten ebenfalls ausgeführt.

Der vollständige HA-Test-Harness enthält durch seinen festen älteren Core-Pin
inzwischen bekannte Advisories in Home-Assistant-Testabhängigkeiten. Der
separate produktionsnahe Runtime-/Unit-Test-Satz verwendet unter anderem
`aiohttp 3.14.5`, `cryptography 50.0.2` und `cbor2 5.9.0`; dessen Audit meldet
keine bekannte Schwachstelle. Das ist keine Behauptung, dass Home Assistant
Core insgesamt schwachstellenfrei sei.

## Hardware

Vom Benutzer real bestätigt ist der reine Wake-on-LAN-Magic-Packet-Test am
GU43TU8079UXZG über WLAN. Der vollständige Samsung-Local-Pfad
(`media_player.turn_on` → Bereitschaft → WebSocket) sowie sämtliche App-Starts
sind noch nicht auf Hardware getestet. Q60C- und Waschmaschinentests stehen
vollständig aus; Details stehen in `COMPATIBILITY.md`.
