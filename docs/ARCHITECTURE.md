# Architektur

## Ziele und Grenzen

Samsung Local ist eine Home-Assistant-Custom-Integration ohne Zusatzdienst.
Home Assistant besitzt Config Entry, Device Registry, Entity Registry,
Zeitplanung und Secrets; der Adapter besitzt genau eine lokale Gerätesession.
Protokolldetails dürfen keine Entity-Klasse erreichen.

```text
Config Flow / Discovery
        |
Authentication Manager ---- gespeicherte lokale Credentials
        |
Adapter Factory
        |
Connection Manager ---- Lock, Backoff, keine Write-Retries
        |
SamsungDeviceAdapter (async contract)
   |-- TizenTvAdapter ---- samsungtvws ---- WS/REST 8001/8002
   |-- OcfApplianceAdapter ---- smartthings-local ---- CoAP/DTLS
   `-- LegacyApplianceAdapter ---- isoliertes HTTPS/TLS1.0 8888
        |
CapabilityRegistry ---- immutable DeviceSnapshot
        |
DataUpdateCoordinator ---- Push/Observe + Poll-Fallback
        |
dynamische HA-Entitäten / Diagnose / Repairs / Abschlussereignis
```

## Adaptervertrag

`SamsungDeviceAdapter` definiert ausschließlich asynchrone Methoden:
`connect`, `disconnect`, `get_device_info`, `get_capabilities`, `get_state`,
`execute_command` und `diagnostics`. Die DTLS-Bibliothek ist synchron; alle
ihre Aufrufe laufen deshalb mit `asyncio.to_thread`. Der TV-Pfad ist nativ
asynchron.

`DeviceInfo`, `Capability`, `WriteSpec` und `DeviceSnapshot` sind eingefrorene,
protokollneutrale Datenklassen. Ein Snapshot bezeichnet nur bestätigte Daten.
Ein gesendeter Befehl schreibt seinen Wunschwert nie in den Snapshot.

## Geräteidentität

Priorität bei OCF: `/oic/d.di`, dann `/oic/p.pi`, dann gemeldete Seriennummer,
zuletzt ein lokaler Host-Fallback. Platzhalter wie `Nothing(SVC)` werden nicht
als stabile Seriennummer verwendet. Bei Tizen führt die REST-Geräte-ID, danach
MAC und erst danach Host. Name und IP sind nie alleinige Identität, sofern eine
bessere Kennung existiert.

## Capability Engine

Die Engine erhält `{href: representation}` aus dem Adapter. Eine Mappingregel
bindet nur, wenn Ressource und benötigte Felder vorhanden sind. Beschreibbare
Funktionen brauchen zusätzlich einen festen `WriteSpec`; unbekannte Daten
werden ausschließlich diagnostiziert.

Bei jedem Snapshot werden Funktionen erneut abgeleitet. Neue Keys werden an
die bereits geladene Plattform weitergegeben. Entfernte Keys bleiben in der
Entity Registry, sind aber unverfügbar; dadurch bleiben Name, Historie und
Automationen stabil.

## Verbindungsmodell

- ein Session-Lock und ein eigener Command-Lock pro Gerät;
- deterministischer lokaler DTLS-Quellport zur Vermeidung verwaister Peer-Slots;
- CoAP Observe für Betriebszustand, Smart Control und Alarme;
- Polling als Fallback und zur periodischen Konsistenzprüfung;
- exponentielles Backoff mit Jitter, begrenzt auf fünf Minuten;
- keine automatische Wiederholung eines Schreibbefehls, da ein verlorenes ACK
  nicht beweist, dass der Befehl nicht ausgeführt wurde;
- TV-REST-Antwort `PowerState=standby/off` ist Standby, ein Timeout nur
  `disconnected`.

## Authentifizierung

TV-Tokens werden beim lokalen Consent-Dialog ausgegeben und im Config Entry
wiederverwendet. OCF verwendet entweder X.509 oder einen bereits autorisierten
PSK über den öffentlichen Authentifizierungsvertrag von `smartthings-local`.
Der automatische OCF-Modus liest einmalig eine öffentliche UUID aus dem
Samsung-Gateway-Zertifikat und mintet lokal ein Identitätszertifikat. Dieser
Schritt ist kontofrei, aber nicht WAN-frei. Manuelle UUID, Zertifikat und PSK
sind offline importierbar.

## Programmende

`CompletionTracker` persistiert nur den Bool-Zustand „zuletzt bereits fertig“.
Er feuert bei einer neuen Finish-Kante genau ein
`samsung_local_program_finished`-Event, bleibt über Reconnect und Neustart
bewaffnet und setzt sich erst bei einem wirklich laufenden neuen Programm
zurück.

## Erweiterung

Ein weiteres Protokoll implementiert den Adaptervertrag. Ein weiteres Gerät
des bestehenden OCF-Protokolls benötigt normalerweise nur mappingspezifische
Regeln und Fixtures. Climate/Fan besitzen bereits Entity-Oberflächen, werden
aber erst erzeugt, wenn ein Adapter eine passende Capability liefert.
