# Samsung Local

Samsung Local ist eine native Home-Assistant-Custom-Integration für die
lokale Steuerung kompatibler Samsung-Geräte. Sie verbindet Tizen-Fernseher
über die lokale WebSocket/REST-Schnittstelle und Haushaltsgeräte über OCF,
CoAP und DTLS. Für unterstützte Funktionen gibt es im laufenden Betrieb
keine SmartThings-Cloud-Abfrage, kein Samsung-Konto und keinen API-Token.

> **Status: 0.1.0 Beta.** Die Softwarearchitektur und simulierten Geräte sind
> getestet. Die drei Zielgeräte wurden noch nicht physisch geprüft. Kein
> Eintrag in der Kompatibilitätsmatrix ist deshalb `confirmed`.

## Funktionen

- UI-Konfiguration, automatische DHCP/SSDP/mDNS-Erkennung und manuelle IP
- Tizen-Pairing mit dauerhaft wiederverwendetem lokalem TV-Token
- Tizen `media_player` und `remote`, HDMI-/App-Auswahl, Navigation und Wiedergabe
- OCF/DTLS mit Zertifikat oder bereits autorisiertem PSK
- lokale Waschmaschinenzustände, Restzeit, Ende, Programme und Einstellungen
- Start/Pause/Stopp nur bei nachgewiesener Ressource und erfüllten Schutzbedingungen
- dynamische Entitäten aus tatsächlich gelesenen Capabilities
- CoAP Observe mit Polling-Fallback, serialisierte Sessions und Reconnect-Backoff
- dedupliziertes Ereignis `samsung_local_program_finished`
- redigierte Home-Assistant-Diagnosen und Repair-Hinweis für unbekannte Ressourcen
- englische und deutsche Oberfläche

## Unterstützte Protokolle

| Gerätetyp | Lokaler Pfad | Status |
|---|---|---|
| Tizen TV (typisch 2016+) | WebSocket/REST auf 8001/8002 | implementiert, Zielgeräte unbestätigt |
| Samsung OCF Appliance | CoAP über zertifikats- oder PSK-authentifiziertes DTLS | implementiert, Zielgerät unbestätigt |
| ältere TP6X-Waschmaschine | HTTPS auf 8888 | konservativ implementiert; Tokenimport erforderlich |
| unbekannte Ressource/Familie | Diagnose only | keine beliebige Schreibschnittstelle |

Welche Entitäten entstehen, entscheidet ausschließlich die Antwort des
Geräts. Modelljahr, Serienname und Firmwarebezeichnung schalten keine
Funktion frei. Insbesondere wird `T-NKLDEUC-2410.0` nicht als eindeutige
Modellkennung behandelt.

## Installation

### HACS (Custom Repository, nach Veröffentlichung)

1. HACS → Integrationen → Drei-Punkte-Menü → Benutzerdefinierte Repositories.
2. Die veröffentlichte Repository-URL eintragen und Kategorie „Integration“ wählen.
3. „Samsung Local“ herunterladen.
4. Home Assistant neu starten.
5. Einstellungen → Geräte & Dienste → Integration hinzufügen → Samsung Local.

Dieses lokale Arbeitsrepository ist noch nicht veröffentlicht. Vorher kann es
manuell installiert werden:

1. `custom_components/samsung_local` nach
   `/config/custom_components/samsung_local` kopieren.
2. Home Assistant neu starten.
3. Samsung Local über die UI hinzufügen.

Ausführlich: [Installation](docs/INSTALLATION.md) und
[Konfiguration](docs/CONFIGURATION.md).

## Geräte hinzufügen

### Fernseher

1. Fernseher und Home Assistant ins gleiche lokale Netz bringen.
2. Bei Bedarf „IP-Fernbedienung“/„Geräteverbindungsmanager“ am TV aktivieren.
3. IP eintragen oder das gefundene Gerät öffnen.
4. „Koppeln“ absenden und den Dialog am Fernseher erlauben.
5. Wake-on-LAN nur aktivieren, wenn eine gültige MAC vorliegt und Broadcasts
   den Fernseher erreichen. Ein fehlgeschlagener Socket gilt nicht als Beweis
   für Standby.

### Haushaltsgerät

Samsung Local bietet vier legitime Wege:

- automatische Zertifikatserzeugung: einmaliger kontofreier Abruf einer
  öffentlichen UUID aus dem Zertifikat von `connect-v2.samsungiotcloud.com`;
- manuelle Eingabe dieser öffentlichen UUID für WAN-freie Einrichtung;
- Import eines vorhandenen Client-Zertifikats;
- Import eines bereits autorisierten lokalen PSK.

Nach dem Pairing erfolgen Status und Befehle ausschließlich lokal. Manche
neueren Geräte lehnen das automatisch erzeugte Zertifikat ab; Samsung Local
umgeht diese Zugriffskontrolle nicht. Der Legacy-Port 8888 benötigt derzeit
einen vorhandenen lokalen Token und ein Client-Zertifikat.

## Typische Entitäten

Nur vorhandene Felder werden angelegt. Möglich sind unter anderem:

- `sensor`: Gerätezustand, Fortschritt, Restzeit, Endzeit, Fehler, Energie
- `binary_sensor`: läuft, Smart Control, Kindersicherung, Betrieb
- `select`: Programm, Temperatur, Schleudern, Spülgänge, App
- `button`: Start, Pause, Stopp
- `switch`: nur bestätigte beschreibbare Funktionen
- `media_player` und `remote`: Tizen-TV

Bild- und Tonmodus, Helligkeit oder aktive Quelle werden **nicht** erfunden:
Sie erscheinen erst, wenn ein lokaler les- und gegebenenfalls beschreibbarer
Endpunkt auf der Hardware nachgewiesen und gemappt ist.

## Beispielautomationen

Die Entity-IDs sind Beispiele. Prüfe vor Verwendung, dass dein Gerät die
betreffende Entität tatsächlich erzeugt hat.

### Waschmaschine fertig

```yaml
triggers:
  - trigger: event
    event_type: samsung_local_program_finished
actions:
  - action: notify.mobile_app_phone
    data:
      message: "Die Waschmaschine ist fertig."
```

### Heimkino einschalten

Voraussetzung: Wake-on-LAN ist für diesen TV funktionsfähig.

```yaml
triggers:
  - trigger: state
    entity_id: input_boolean.home_cinema
    to: "on"
actions:
  - action: media_player.turn_on
    target:
      entity_id: media_player.living_room_tv
```

### TV im Schlafmodus ausschalten

```yaml
triggers:
  - trigger: state
    entity_id: input_boolean.sleep_mode
    to: "on"
actions:
  - action: media_player.turn_off
    target:
      entity_id: media_player.bedroom_tv
```

### Waschmaschinenfehler melden

Voraussetzung: Das Gerät meldet `/alarms/vs/0` und erzeugt einen
`error_code`-Sensor.

```yaml
triggers:
  - trigger: state
    entity_id: sensor.washer_error_code
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.state not in ['none', 'unknown', 'unavailable'] }}"
actions:
  - action: notify.mobile_app_phone
    data:
      message: "Waschmaschinenfehler: {{ trigger.to_state.state }}"
```

### Auf bestätigten TV-Status reagieren

```yaml
triggers:
  - trigger: state
    entity_id: media_player.living_room_tv
    to: "on"
actions:
  - action: light.turn_down
    target:
      area_id: living_room
```

## Offline-Betrieb und Sicherheit

- Der laufende Gerätepfad enthält keine SmartThings- oder Account-API.
- Der optionale öffentliche UUID-Abruf findet nur im ausdrücklich gewählten
  automatischen Einrichtungsmodus statt.
- Private Schlüssel, TV-Tokens, IPs, MACs, Seriennummern und Namen werden in
  Diagnosen redigiert.
- Ein Schreibfehler verändert keinen bestätigten Entity-Zustand.
- Kindersicherung und Türverriegelung werden nicht umgangen.
- TLS-Relaxierung für das erzwungene Legacy-TLS-1.0-Profil ist auf genau den
  8888-Adapter begrenzt.

Der Samsung-Endpunkt selbst kann unabhängig von dieser Integration weiterhin
Samsung-Server kontaktieren. Samsung Local blockiert diesen Verkehr nicht.

## Bekannte Einschränkungen

- Keine reale Hardwareprüfung der drei Zielgeräte in diesem Repository.
- OCF-PKI-Firmware kann ein anderes, vorab autorisiertes Zertifikat/PSK verlangen.
- Automatische Token-Ausgabe mit Callback-Port 8889 ist für Legacy-Geräte noch
  nicht implementiert; ein Token muss importiert werden.
- Bild-/Tonmodus und exakte TV-Lautstärke benötigen einen nachgewiesenen lokalen
  Status-/Schreibkanal und sind daher derzeit nicht als eigene Entität aktiv.
- Apps werden nur angeboten, wenn der TV seine installierte App-Liste liefert.
- Haushaltsgeräte können nur eine lokale Session zulassen; eine zweite lokale
  Integration kann Verbindungen verdrängen.

Siehe [Kompatibilität](docs/COMPATIBILITY.md),
[Fehlerbehebung](docs/TROUBLESHOOTING.md) und [Roadmap](docs/ROADMAP.md).
Die noch vom Repository-Eigentümer auszufüllenden Veröffentlichungsschritte
stehen in [Veröffentlichung](docs/PUBLICATION.md).

## Entwicklung und Mitwirkung

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install '.[test,dev]'
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components tests
```

Für neue Hardware bitte zuerst die redigierte Diagnose und die Schritte aus
[Hardwaretests](docs/HARDWARE_TESTING.md) verwenden. Niemals reale Tokens,
private Schlüssel, IPs, MACs oder Seriennummern veröffentlichen.

Samsung Local ist ein unabhängiges, nicht von Samsung autorisiertes Projekt.
„Samsung“ und „SmartThings“ sind Marken ihrer jeweiligen Inhaber.
