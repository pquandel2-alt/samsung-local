# Technische Untersuchung

Stand der Untersuchung: 11. Oktober 2026. Die Upstreams wurden nur lesend in
einem temporären Verzeichnis ausgecheckt; kein fremdes Repository wurde
verändert.

## LocalThings

- Repository: <https://github.com/mbillow/localthings>
- untersuchter Stand: `v0.34.0`, Commit
  `26c96a1fe28af2325508bc708fb4246f04e4a1d2` vom 10.10.2026
- Lizenz: MIT
- Testkorpus: 373 Dateien im untersuchten `tests/`-Baum

Ergebnis: LocalThings ist die reifste Referenz für Samsung-Haushaltsgeräte.
Es trennt Transport, Registry und Entities, verwendet OCF-Standardressourcen
vor Samsung-Fallbacks, liest `/oic/d`, `/oic/p`, `/oic/res` und `/device/0`,
nutzt Observe plus gestuftes Polling, führt Reauth/Reconfigure aus, folgt
geänderten DHCP-Adressen und redigiert Diagnosefelder. Neuere Geräte sprechen
zertifikatsauthentifiziertes CoAP/DTLS; bekannte ältere Familien verwenden
HTTPS 8888. Ein Appliance kann nur eine lokale Session akzeptieren.

Entscheidung: Der Protokollstack wird nicht nachgebaut; Samsung Local verwendet
dieselbe veröffentlichte Bibliothek `smartthings-local`. Die LocalThings-
Integration selbst ist kein importierbares Protokollpaket und darf nicht als
zweite installierte HA-Integration vorausgesetzt werden. Daher besitzt Samsung
Local eine eigene, kleinere Registry für nachgewiesene Zielgerätefelder.
Konzept und Feldsemantik wurden untersucht, aber keine LocalThings-Datei wird
vendored.

## SmartThings-Local

- Repository: <https://github.com/QuiteYellow/SmartThings-Local>
- untersuchter Commit:
  `7f96fdfbc89c63fb188bb378526018637221c74d` vom 10.10.2026
- PyPI: `smartthings-local==0.1.24`
- Lizenz: MIT; zusätzliches NOTICE mit Markenhinweis
- Testkorpus: 53 Dateien

Die Bibliothek implementiert DTLS-Sessions mit X.509 oder PSK, CoAP GET/POST,
Block2, Observe, Message-ID/Token-Verwaltung, Ratenbegrenzung, ClientHello-
Portprobe und klassifizierte Fehler. Sie unterstützt explizite Samsung-
Serverprofile mit Zertifikatsprüfung. Ihre Session-API ist synchron und besitzt
einen Reader-Thread; Samsung Local kapselt alle blockierenden Aufrufe mit
`asyncio.to_thread` und führt Push-Callbacks thread-sicher in den HA-Loop.

Nicht jede Firmware akzeptiert das verbreitete selbstsignierte
Identitätsprofil. Erreichbarkeit, DTLS-Authentifizierung, ACL-Autorisierung und
OCF-Ownership sind getrennte Zustände. Samsung Local implementiert keine
Ownership-Übernahme oder Sicherheitsumgehung.

## samsung-tv-ws-api

- Repository: <https://github.com/xchwarze/samsung-tv-ws-api>
- untersuchter Stand: `v3.0.6`, Commit
  `e48d6377faede37db1f034d726a079b9d8034fac`
- Lizenz: LGPL-3.0
- Testkorpus: 30 Dateien

Die Bibliothek bietet synchrone und asynchrone WebSocket-/REST-Clients,
Token-Pairing, Remote Keys, installierte Apps, App-Start/-Ende und einen
verschlüsselten älteren API-Pfad. Samsung Local verwendet ausschließlich die
asynchronen modernen Tizen-Klassen. Die Bibliothek wird unverändert als
dynamisches Python-Paket installiert; `THIRD_PARTY_NOTICES.md` nennt Lizenz und
Urheber.

## Offizielle Home-Assistant-Integration `samsungtv`

- Quellstand: Home Assistant Core Commit
  `1df3b779e8f6e3576c3c259450f63557dc705c74` vom 11.10.2026
- Manifest: Gold-Quality, lokale Push-Klasse, `samsungtvws==3.0.6`, SSDP,
  Zeroconf und DHCP
- Architektur: Bridge pro Protokollgeneration, DataUpdateCoordinator,
  Media Player, Remote, Tokenpersistenz, REST-Info und UPnP

Übernommene Entscheidungen: Ports 8002/8001 in dieser Reihenfolge, Pairing am
TV, REST-Geräteinfo als Modellquelle, keine Ableitung der Generation allein
aus Firmwaretext, Close/Reload-Lifecycle und separate Remote-Entity.

Bewusste Abweichung: Ein fehlgeschlagener Socket wird in Samsung Local nicht
als Standby bezeichnet. Wake-on-LAN benötigt eine gültige MAC und eine
Benutzeroption. Die ältere verschlüsselte PIN-API ist in 0.1.0 noch nicht in
den Adapter aufgenommen.

## Weitere Projekte

`TheFab21/ha-samsungtv-smart` wurde als gepflegte lokale TV-Referenz geprüft.
Sein zusätzlicher Samsung-IP-Control-Kanal kann lokal Bildmodus, Eingang und
weitere Werte liefern, ist aber noch nicht ausreichend über die beiden
Zielgeräte verifiziert. Cloud-/OAuth-Funktionen dieses Projekts widersprechen
dem Laufzeitziel von Samsung Local und werden nicht übernommen. IP Control ist
ein Kandidat für eine spätere, getrennte Adaptererweiterung.

## Resultierende Risiken

1. WW90T554AAE/S2 ist weder durch Modellname noch Controller-Version sicher
   einem Authprofil zuzuordnen; ein Hardware-Probe ist zwingend.
2. App-Liste und Remote Keys variieren bei Tizen trotz gleicher API.
3. Bild-/Tonmodus ist über den Standard-WebSocket nicht allgemein lesbar.
4. Wake-on-LAN hängt von TV-Einstellung, LAN/WLAN und Broadcast-Routing ab.
5. Samsung-Firmware kann Ressourcen hinzufügen oder entfernen; deshalb
   Live-Discovery, stabile Keys und Repairs statt Modelltemplates.

