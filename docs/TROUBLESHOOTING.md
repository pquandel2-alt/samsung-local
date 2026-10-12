# Fehlerbehebung

## Gerät nicht erreichbar

- IP in Router/DHCP prüfen und „Neu konfigurieren“ verwenden;
- Client-Isolation/VLAN-Regeln prüfen;
- TV/Appliance aufwecken, dann erneut versuchen;
- keine zweite lokale Integration gleichzeitig verbinden lassen;
- bei OCF UDP 49152–49160 bzw. den beworbenen Port und 5684 im LAN prüfen;
- bei Tizen TCP 8001/8002, bei Legacy TCP 8888 prüfen.

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

## Fehlende Funktion

Wenn unter Reparaturen „Neue lokale Samsung-Funktionen“ erscheint, Diagnose
herunterladen, selbst nochmals auf Secrets prüfen und zusammen mit Modell,
Firmware und beobachtetem Verhalten melden. Keine unredigierten Paketmitschnitte
öffentlich hochladen.
