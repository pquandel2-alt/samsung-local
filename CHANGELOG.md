# Changelog

Alle wesentlichen Änderungen an Samsung Local werden hier dokumentiert. Das
Projekt verwendet [Semantic Versioning](https://semver.org/).

## [Unreleased]

- Hardwarevalidierung für die drei Zielgeräte steht aus.
- Veröffentlichung und Aufnahme in den HACS-Standardkatalog stehen aus.

## [0.1.0-beta.1] - 2026-10-11

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

[Unreleased]: https://github.com/samsung-local/samsung-local/compare/v0.1.0-beta.1...HEAD
[0.1.0-beta.1]: https://github.com/samsung-local/samsung-local/releases/tag/v0.1.0-beta.1
