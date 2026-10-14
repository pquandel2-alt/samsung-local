# Changelog

Alle wesentlichen Änderungen an Samsung Local werden hier dokumentiert. Das
Projekt verwendet [Semantic Versioning](https://semver.org/).

## [Unreleased]

- Weitere Hardwarevalidierung für App-Starts, den vollständigen WOL-Ablauf
  und die Haushaltsgeräte steht aus.
- Aufnahme in den HACS-Standardkatalog steht aus; die Installation als
  benutzerdefiniertes HACS-Repository ist vorbereitet.

## [0.1.0-beta.5] - 2026-10-14

### Fixed

- `wakeonlan` auf die von Home Assistant verwendete Version 3.3.0 gepinnt,
  damit Hassfest und die Home-Assistant-Abhängigkeitsauflösung konfliktfrei
  bleiben. Der in Beta 4 eingeführte WOL-Code bleibt funktional unverändert.

## [0.1.0-beta.4] - 2026-10-14

### Added

- Integriertes, bestätigtes Wake-on-LAN mit gerätespezifischer MAC,
  Broadcast-Adresse, UDP-Port, Timeout, begrenzten Versuchen und UI-Test.
- Gerätespezifische Tizen-App-Registry mit bekannten Kandidaten, automatischer
  Erkennung, manuellen IDs, Aliasen und DEEP_LINK/NATIVE_LAUNCH/REST.
- Gemeinsamer App-Launcher für `media_player.select_source`,
  `media_player.play_media` und `samsung_local.launch_app`, einschließlich
  optionalem Wake-on-LAN und Reconnect.
- Sichere App-/Power-Diagnosen und Homeintent-Integrationsanleitung.
- Reiner Wake-on-LAN-Hardwaretest am GU43TU8079UXZG bestätigt; vollständiger
  Samsung-Local-Pfad und reale App-Starts stehen noch aus.

## [0.1.0-beta.3] - 2026-10-12

### Fixed

- Automatische Statusaktualisierungen dürfen kein interaktives TV-Pairing mehr
  starten. Fehlt der gespeicherte Token oder ersetzt der Fernseher ihn
  unerwartet, wechselt die Integration kontrolliert in die Reauthentifizierung.
- Ein Pairing eines tokenpflichtigen Fernsehers gilt nur noch dann als
  erfolgreich, wenn ein wiederverwendbarer Token geliefert wurde.
- Die Fehlerbehebung dokumentiert Samsungs Einstellung
  „Zugriffsbenachrichtigung – Nur beim ersten Mal“.

## [0.1.0-beta.2] - 2026-10-12

### Fixed

- Mehrfache SSDP-Discovery-Karten desselben Fernsehers werden durch engere
  Service-Matcher und hostübergreifende Flow-Deduplizierung verhindert.
- Der TV-Pairing-Dialog weist auf den erforderlichen eingeschalteten Zustand
  hin und meldet einen fehlgeschlagenen Pairing-Kanal handlungsorientiert.

## [0.1.0-beta.1] - 2026-10-12

### Added

- Native Home-Assistant-Custom-Integration mit UI-, Options-, Reconfigure- und
  Reauthentication-Flows.
- Generischer Tizen-TV-Adapter für lokale REST-/WebSocket-Kommunikation,
  Pairing-Tokens, Fernbedienung, Apps, HDMI und optionales Wake-on-LAN.
- OCF-Haushaltsgeräteadapter auf Basis von `smartthings-local` mit DTLS,
  Zertifikat/PSK, Observe und Polling-Fallback.
- Isolierter, konservativer HTTPS-8888-Adapter für nachgewiesene
  TP6X-Waschmaschinenprofile.
- Dynamische Capability Engine, Connection Manager, Abschlussereignis,
  redigierte Diagnosen und Repair-Hinweis für unbekannte Ressourcen.
- Deutsche und englische Oberfläche, HACS-Metadaten, CI-Konfiguration,
  Tests, Sicherheits-, Installations-, Migrations- und Hardwaretestdokumente.

[Unreleased]: https://github.com/pquandel2-alt/samsung-local/compare/v0.1.0-beta.5...HEAD
[0.1.0-beta.5]: https://github.com/pquandel2-alt/samsung-local/compare/v0.1.0-beta.4...v0.1.0-beta.5
[0.1.0-beta.4]: https://github.com/pquandel2-alt/samsung-local/compare/v0.1.0-beta.3...v0.1.0-beta.4
[0.1.0-beta.3]: https://github.com/pquandel2-alt/samsung-local/compare/v0.1.0-beta.2...v0.1.0-beta.3
[0.1.0-beta.2]: https://github.com/pquandel2-alt/samsung-local/compare/v0.1.0-beta.1...v0.1.0-beta.2
[0.1.0-beta.1]: https://github.com/pquandel2-alt/samsung-local/releases/tag/v0.1.0-beta.1
