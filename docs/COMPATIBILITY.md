# Hardware-Kompatibilität

Statuswerte: `confirmed`, `reported`, `implemented_unverified`, `partial`,
`unsupported`, `unknown`. Mock-Tests zählen nie als Hardwarebestätigung.

## Samsung WW90T554AAE/S2

| Bereich | Status | Begründung |
|---|---|---|
| Discovery | `implemented_unverified` | begrenzte OCF-DTLS- und 8888-Probe implementiert |
| Verbindung | `implemented_unverified` | OCF/DTLS und konservativer TP6X-8888-Pfad vorhanden; echtes Protokoll unbekannt |
| Authentifizierung | `implemented_unverified` | X.509, PSK und Legacy-Import vorhanden; Geräteprofil nicht geprüft |
| Statusabfrage | `implemented_unverified` | Washer-Ressourcen gemappt, Fixture ist synthetisch |
| Steuerung | `implemented_unverified` | OCF Start/Pause/Stopp mit Smart-Control-Gate; Gerät kann Writes verweigern |
| Entitätenerkennung | `implemented_unverified` | dynamische Feldprüfung vorhanden |
| Reconnect | `implemented_unverified` | simuliert geprüft, nicht auf Hardware |
| Offline-Betrieb | `implemented_unverified` | Software-WAN-Sperre geprüft; Hardware-WAN-Sperre fehlt |

Die Controller-Angabe `WS.5.1.32` beweist kein Protokoll. Benötigt wird zuerst
eine redigierte Diagnose nach dem Ablauf in `HARDWARE_TESTING.md`.

## Samsung GQ55Q60CAUXZG (Q60C, 55 Zoll)

| Bereich | Status | Begründung |
|---|---|---|
| Discovery | `implemented_unverified` | REST 8002/8001, SSDP, DHCP und AirPlay-mDNS implementiert |
| Verbindung | `implemented_unverified` | asynchroner Tizen-WebSocket implementiert |
| Authentifizierung | `implemented_unverified` | lokales Consent-Token implementiert |
| Statusabfrage | `implemented_unverified` | REST `PowerState`; kein Hardwaretest |
| Steuerung | `implemented_unverified` | Remote Keys, Apps, HDMI, Wiedergabe implementiert |
| Entitätenerkennung | `implemented_unverified` | App-Auswahl nur bei echter App-Liste |
| Reconnect | `implemented_unverified` | simuliert geprüft |
| Offline-Betrieb | `implemented_unverified` | Softwarepfad lokal; WAN-blockierter TV-Test fehlt |

Bild-/Tonmodus und Helligkeit sind `unknown`, nicht als funktionierende
Entitäten implementiert, weil dafür auf diesem Modell noch kein lokaler
Endpunkt nachgewiesen wurde.

## Samsung 8 Series (43), Firmware T-NKLDEUC-2410.0

| Bereich | Status | Begründung |
|---|---|---|
| Discovery | `implemented_unverified` | derselbe generische Tizen-Probeweg |
| Verbindung | `implemented_unverified` | Modell wird per REST abgefragt, nicht aus Firmware abgeleitet |
| Authentifizierung | `implemented_unverified` | Token-Pairing vorhanden |
| Statusabfrage | `implemented_unverified` | Standby nur nach REST-Antwort |
| Steuerung | `implemented_unverified` | gemeinsame Tizen-Befehle vorhanden |
| Entitätenerkennung | `implemented_unverified` | capabilities geräteabhängig |
| Reconnect | `implemented_unverified` | simuliert geprüft |
| Offline-Betrieb | `implemented_unverified` | Hardwaretest fehlt |

Die genaue Modellnummer ist `unknown`. Die Firmware ist ausdrücklich keine
Ersatz-Modellnummer.

