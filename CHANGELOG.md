# Changelog

Alle wesentlichen Änderungen an Samsung Local werden hier dokumentiert. Das
Projekt verwendet [Semantic Versioning](https://semver.org/).

## [Unreleased]

- Hardwarevalidierung für die drei Zielgeräte steht aus.
- Aufnahme in den HACS-Standardkatalog steht aus; die Installation als
  benutzerdefiniertes HACS-Repository ist vorbereitet.

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

[Unreleased]: https://github.com/pquandel2-alt/samsung-local/compare/v0.1.0-beta.1...HEAD
[0.1.0-beta.1]: https://github.com/pquandel2-alt/samsung-local/releases/tag/v0.1.0-beta.1
