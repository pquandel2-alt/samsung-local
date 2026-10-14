# Hardware-Testanleitung

Diese Schritte machen aus `implemented_unverified` erst nach dokumentiertem
Erfolg `confirmed`.

## Vorbereitung

1. Backup von Home Assistant erstellen.
2. Gerät nicht aus SmartThings entfernen und nicht zurücksetzen.
3. IP/MAC/Seriennummer in Screenshots und Logs redigieren.
4. Andere lokale Samsung-Appliance-Integrationen vor dem DTLS-Test entladen;
   SmartThings Cloud darf zum Vergleich bleiben.
5. Debug-Logging nur zeitlich begrenzt aktivieren:

```yaml
logger:
  logs:
    custom_components.samsung_local: debug
    smartthings_local: debug
    samsungtvws: debug
```

## Waschmaschine WW90T554AAE/S2

1. Auto-Discovery und manuelle IP getrennt testen.
2. Bei wachem Gerät verbinden und Authprofil notieren.
3. Diagnose herunterladen; prüfen, dass keine IP/MAC/Seriennummer/Keys sichtbar sind.
4. Tür/Kindersicherung/Smart Control in beiden Stellungen beobachten.
5. Programm, Temperatur, Schleudern und Spülen am Panel ändern; Entity-Abgleich.
6. Mit Smart Control aus Start/Pause verweigern lassen.
7. Mit Smart Control einen harmlosen Zyklus starten, pausieren, stoppen.
8. Vollständigen Zyklus laufen lassen; genau ein Finish-Event prüfen.
9. Während des Laufs WLAN trennen, wieder verbinden, Zustand rekonstruieren.
10. HA neu starten und Wiederverbindung prüfen.

## Fernseher

Für beide TVs separat:

1. Pairing erlauben, HA neu starten, kein zweiter Consent-Dialog erwartet.
2. Gerätinfo und echte Modellnummer prüfen.
3. Navigation, Lautstärke, Mute, Play/Pause/Stop und HDMI einzeln testen.
4. Automatisch erkannte Apps testen. Liefert der TV keine Liste, Netflix und
   Prime mit jeweils einer begrenzten Kandidaten-ID im Options Flow testen;
   DEEP_LINK, NATIVE_LAUNCH und REST nur einzeln und dokumentiert wechseln.
5. Ausschalten: Standby muss durch Geräteantwort bestätigt werden.
6. LAN-Verbindung bei eingeschaltetem TV trennen: Zustand muss `unavailable`/
   getrennt statt fälschlich `off` werden.
7. Wake-on-LAN mit Ethernet/WLAN und nach 1, 10 und 30 Minuten Standby prüfen.
8. `media_player.turn_on` ausführen: Es darf erst nach erreichbarem REST und
   WebSocket `on` ergeben und bei Nichtreaktion nur begrenzt versuchen.
9. `samsung_local.launch_app`, `media_player.select_source` und
   `media_player.play_media` für dieselbe App vergleichen.
10. App-Start aus mindestens zehn Minuten Standby prüfen: WOL → Reconnect →
    genau ein Start. Zwei schnelle verschiedene App-Aufträge ebenfalls testen.

Für den GU43TU8079UXZG ist der reine Magic-Packet-Test über WLAN bereits vom
Benutzer bestätigt. Die Schritte 8–10 bleiben trotzdem offen. Beim Q60C ist
auch Schritt 7 noch offen. Reale MAC-Adressen gehören nicht in Berichte.

## WAN-Sperrtest

Nach erfolgreichem Pairing am Router nur Internetzugriff des HA-Hosts sperren,
LAN intern erlauben. Status, Writes, HA-Neustart und Reconnect testen. Danach
optional auch das Samsung-Gerät vom WAN trennen. Auswirkungen auf Gerätelogin,
WLAN und Firmware sind Geräteverhalten, nicht Samsung Local.

Zu melden: HA-Version, Integrationsversion, Modell, Firmware, Protokoll,
Testschritt und redigierte Diagnose. Keine Secrets.
