# Fehlerbehebung

## Gerät nicht erreichbar

- IP in Router/DHCP prüfen und „Neu konfigurieren“ verwenden;
- Client-Isolation/VLAN-Regeln prüfen;
- TV/Appliance aufwecken, dann erneut versuchen;
- keine zweite lokale Integration gleichzeitig verbinden lassen;
- bei OCF UDP 49152–49160 bzw. den beworbenen Port und 5684 im LAN prüfen;
- bei Tizen TCP 8001/8002, bei Legacy TCP 8888 prüfen.

## Derselbe Fernseher wird mehrfach gefunden

Auf `0.1.0-beta.2` oder neuer aktualisieren und Home Assistant neu starten.
Ältere Versionen reagierten auf mehrere SSDP-Dienste desselben Fernsehers.
Offene alte Discovery-Karten können nach dem Neustart verworfen werden; die
neue Erkennung legt pro Host nur noch einen Einrichtungsdialog an.

## TV-Pairing schlägt fehl

Der Fernseher muss für die einmalige Kopplung vollständig eingeschaltet sein;
eine im Standby erreichbare REST-Antwort genügt nicht für den WebSocket-
Freigabedialog. In den TV-Einstellungen die IP-/lokale Fernsteuerung bzw. den
Geräteverbindungsmanager aktivieren, Samsung Local erneut senden und den
Dialog direkt am Fernseher erlauben.

## Der Fernseher fragt wiederholt nach Zugriffsfreigabe

Samsung Local darf interaktives Pairing nur im Einrichtungs- oder Reauth-Flow
starten. Ab `0.1.0-beta.3` öffnet ein Hintergrund-Refresh ohne gespeicherten
Token keinen Pairing-Kanal mehr, sondern fordert kontrolliert eine erneute
Authentifizierung an.

Am Fernseher zusätzlich unter **Einstellungen > Allgemein > Netzwerk >
Experteneinstellungen > Geräteverbindungsmanager** (Bezeichnungen variieren je
nach Firmware) die **Zugriffsbenachrichtigung** auf **Nur beim ersten Mal**
stellen. Alte oder doppelte Einträge für Home Assistant/Samsung Local in der
Geräteliste entfernen und anschließend genau einmal über den Reauth-Dialog neu
koppeln. Die Einstellung **Immer fragen** erzeugt bei jeder legitimen
Wiederverbindung erneut einen Dialog, auch wenn die Integration korrekt arbeitet.

## Authentifizierung abgelehnt

Beim TV den Eintrag im Geräteverbindungsmanager löschen und Reauth ausführen.
Bei OCF nicht wiederholt mit zufälligen Zertifikaten probieren: Importmodus oder
ein legitimer autorisierter PSK ist erforderlich. Samsung Local setzt keine
Ownership zurück. Legacy benötigt derzeit einen schon vorhandenen Token.

## Fernsteuerung deaktiviert

Tür schließen und Smart Control/Fernsteuerung am Gerät aktivieren. Die Option
für unkritische Einstellungen ist nur für nachweislich abweichende Firmware
gedacht; Start/Pause können dieses Gate niemals umgehen.

## TV wird als getrennt statt aus angezeigt

Das ist beabsichtigt: Netzwerkfehler sind kein Standby-Beweis. Prüfe die
REST-Erreichbarkeit und Strom-/Deep-Standby-Einstellungen. Wake-on-LAN braucht
oft dasselbe Layer-2-Netz und funktioniert je nach TV über Ethernet
zuverlässiger als WLAN.

## Wake-on-LAN oder App-Start schlägt fehl

Unter Samsung Local → Konfigurieren → Optionen zuerst MAC, Broadcast/Ziel,
UDP-Port und Zeitlimit prüfen. Danach „Wake-on-LAN testen“ verwenden. Erfolg
bedeutet, dass nicht nur das Paket gesendet wurde, sondern auch REST und
Tizen-WebSocket wieder bereit waren. Bei VLANs ist häufig die gerichtete
Broadcast-Adresse des TV-Netzes erforderlich.

Für Apps zuerst „App testen“ verwenden. Liefert der Fernseher keine App-Liste,
eine gerätespezifische ID und das Startverfahren hinterlegen. Die bekannten
IDs sind keine Installationsgarantie. In der redigierten Diagnose zeigen
`command_sent`, `device_confirmed` und `active`, wie weit der lokale Ablauf
beobachtbar war. Nicht blind wiederholen: Ein gesendeter Befehl kann trotz
nicht lesbarem Aktivstatus erfolgreich gewesen sein.

## Fehlende Funktion

Wenn unter Reparaturen „Neue lokale Samsung-Funktionen“ erscheint, Diagnose
herunterladen, selbst nochmals auf Secrets prüfen und zusammen mit Modell,
Firmware und beobachtetem Verhalten melden. Keine unredigierten Paketmitschnitte
öffentlich hochladen.
