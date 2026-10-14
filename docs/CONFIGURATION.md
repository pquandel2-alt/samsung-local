# Konfiguration

## UI-Ablauf

1. Samsung Local auswählen.
2. Erkannte Geräte bestätigen oder eine einzelne IP/Hostname eingeben.
3. Auto, Tizen, OCF oder Legacy auswählen.
4. Den lokalen Authentifizierungsschritt abschließen.
5. Angezeigtes Modell, Protokoll und Zahl erkannter Funktionen prüfen.
6. Gerät hinzufügen.

Die manuelle Eingabe prüft ausschließlich bekannte Ports dieses Hosts. Es gibt
keinen Subnetz- oder unbegrenzten Portscan.

## OCF-Modi

- **auto_online:** einmaliger öffentlicher UUID-Abruf ohne Konto;
- **manual_identity:** derselbe Zertifikatstyp, aber UUID lokal eingegeben;
- **certificate:** vorhandenes Zertifikat und passender privater Schlüssel;
- **psk:** bereits autorisierte UUID-Identität plus 16/32-Byte-Hexschlüssel.

Ein Reset oder Ownership-Wechsel wird nicht ausgeführt. Zugangsdaten lassen
sich über Reauth erneuern.

## Optionen

- Polling 10–300 Sekunden, Standard 30;
- automatischer Reconnect ein-/ausschaltbar;
- Wake-on-LAN: nur TV, MAC, IPv4-Broadcast/Ziel, UDP-Port, Einschaltzeitlimit
  und 1–5 begrenzte Paketversuche;
- bestätigter Wake-on-LAN-Test: Erfolg erst nach REST- und WebSocket-Antwort;
- pro TV Apps hinzufügen/ersetzen/entfernen, mehrere IDs und eindeutige
  Aliase pflegen sowie App-Start testen;
- „Unkritische Einstellungen trotz Smart Control off“: Ausnahme für
  Programmeinstellungen, die das Gerät nachweislich annimmt; standardmäßig
  aus und niemals für Start/Pause wirksam;
- zusätzliche Diagnose: bleibt auch dann geheimnisredigiert.

Die MAC des GU43TU8079UXZG wird nicht im Quellcode hinterlegt. Sie wird nur im
Options Flow des konkreten Config Entry gespeichert. Für den Q60C müssen
MAC/Broadcast und Wake-Funktion separat getestet werden.

## App-Zuordnung

Automatische Erkennung hat Vorrang. Wenn die Firmware keine App-Liste liefert,
kann eine App manuell mit stabilem Schlüssel, Anzeigename, kommaseparierten
IDs, Aliasen und Startverfahren (`auto`, `DEEP_LINK`, `NATIVE_LAUNCH`, `REST`)
angelegt werden. `auto` verwendet zuerst den WebSocket-DEEP_LINK und wechselt
nur nach einem echten Übertragungsfehler auf REST; ein nicht verifizierbarer,
aber gesendeter Start wird nicht mehrfach ausgelöst.

Bekannte Netflix-, Prime-Video- und weitere IDs dienen nur als begrenzte
Kandidaten. Sie beweisen weder Installation noch regionale Kompatibilität.

## Reconfigure

„Neu konfigurieren“ ändert die IP/den Host, prüft denselben Protokolltyp und
behält eindeutige ID, Entities, Historie und Automationen.
