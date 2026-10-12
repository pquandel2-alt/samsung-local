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
- Wake-on-LAN: nur TV, MAC und geeignetes Broadcast-Netz erforderlich;
- „Unkritische Einstellungen trotz Smart Control off“: Ausnahme für
  Programmeinstellungen, die das Gerät nachweislich annimmt; standardmäßig
  aus und niemals für Start/Pause wirksam;
- zusätzliche Diagnose: bleibt auch dann geheimnisredigiert.

## Reconfigure

„Neu konfigurieren“ ändert die IP/den Host, prüft denselben Protokolltyp und
behält eindeutige ID, Entities, Historie und Automationen.
