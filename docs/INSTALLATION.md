# Installation

## Voraussetzungen

- Home Assistant 2026.9 oder neuer (Python 3.14.2+ in Core/HAOS)
- Home Assistant und Gerät im selben erreichbaren lokalen Netz
- feste DHCP-Zuordnung empfohlen, aber nicht zwingend
- keine zweite lokale Appliance-Integration, die gleichzeitig dieselbe
  Einzelsession beansprucht

## HACS

Das Repository muss zuerst veröffentlicht sein. Danach in HACS unter
„Benutzerdefinierte Repositories“ die URL als Integration hinzufügen,
Samsung Local herunterladen und Home Assistant neu starten. Eine Aufnahme in
den HACS-Standardkatalog ist nicht Bestandteil dieses lokalen Builds.

## Manuell

1. Repository herunterladen.
2. Den vollständigen Ordner `custom_components/samsung_local` nach
   `/config/custom_components/samsung_local` kopieren.
3. Dateirechte prüfen: Home Assistant muss die Dateien lesen können.
4. Home Assistant neu starten.
5. Unter Einstellungen → Geräte & Dienste → Integration hinzufügen nach
   „Samsung Local“ suchen.

Keine PEM- oder Key-Datei gehört in den Integrationsordner. Zugangsdaten werden
im UI-Flow eingegeben und im Home-Assistant-Config-Entry gespeichert. Sichere
Backups von Home Assistant schützen deshalb auch diese Secrets.

## Entfernen

Zuerst den Samsung-Local-Config-Entry in Home Assistant entfernen, dann bei
Bedarf die Dateien löschen. Vorhandene SmartThings-Integrationen oder
Automationen werden von Samsung Local nie automatisch verändert.

