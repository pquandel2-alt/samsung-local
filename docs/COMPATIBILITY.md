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

Wake-on-LAN und App-Starts sind für diesen Q60C softwareseitig vorhanden,
aber MAC, Broadcast-Verhalten, App-IDs und Startverfahren wurden noch nicht am
Gerät geprüft. Der Options Flow enthält deshalb getrennte WOL- und App-Tests.

Bild-/Tonmodus und Helligkeit sind `unknown`, nicht als funktionierende
Entitäten implementiert, weil dafür auf diesem Modell noch kein lokaler
Endpunkt nachgewiesen wurde.

## Samsung GU43TU8079UXZG (TU8079, 43 Zoll), Firmware T-NKLDEUC-2410.0

| Bereich | Status | Begründung |
|---|---|---|
| Discovery | `implemented_unverified` | derselbe generische Tizen-Probeweg |
| Verbindung | `implemented_unverified` | Modell wird per REST abgefragt, nicht aus Firmware abgeleitet |
| Authentifizierung | `implemented_unverified` | Token-Pairing vorhanden |
| Statusabfrage | `implemented_unverified` | Standby nur nach REST-Antwort |
| Steuerung | `partial` | Magic Packet an WLAN-MAC wurde real bestätigt; neuer Samsung-Local-WOL-/App-Pfad noch nicht auf Hardware geprüft |
| Entitätenerkennung | `implemented_unverified` | capabilities geräteabhängig |
| Reconnect | `implemented_unverified` | simuliert geprüft |
| Offline-Betrieb | `implemented_unverified` | Hardwaretest fehlt |

Die Modellnummer wurde inzwischen als GU43TU8079UXZG angegeben. Die Firmware
bleibt ausdrücklich keine Ersatz-Modellnummer. Der erfolgreiche reale Test
bestand aus `wake_on_lan.send_magic_packet` an die WLAN-MAC. Er bestätigt die
Hardwarefähigkeit, aber noch nicht den vollständigen neuen Ablauf aus
`media_player.turn_on`, Bereitschaftsprüfung, Token-Reconnect und App-Start.

## Funktionsdetails für beide Fernseher

| Funktion | GU43TU8079UXZG | GQ55Q60CAUXZG |
|---|---|---|
| Magic Packet erreicht Hardware | `confirmed` | `unknown` |
| Samsung-Local `media_player.turn_on` | `implemented_unverified` | `implemented_unverified` |
| Netflix/Prime/weitere Apps | `implemented_unverified` | `implemented_unverified` |
| App-Aktivstatus lesbar | `unknown` | `unknown` |
