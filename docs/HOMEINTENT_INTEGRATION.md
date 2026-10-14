# Homeintent-Anbindung

Samsung Local besitzt keine feste Homeintent-Abhängigkeit. Homeintent wählt
eine Home-Assistant-Entity aus und ruft normale Home-Assistant-Aktionen auf;
App-IDs, Tizen-WebSockets und Wake-on-LAN bleiben vollständig in Samsung Local.

## Zielfernseher und Apps

Homeintent soll Räume oder Gerätenamen auf die jeweilige `media_player`-Entity
abbilden. Zwei Fernseher mit Netflix werden dadurch über ihre Entity-ID und
nicht über die App unterschieden.

`app` akzeptiert den registrierten Schlüssel, Anzeigenamen, einen eindeutigen
Alias oder eine registrierte App-ID. Groß-/Kleinschreibung, Leerzeichen und
Satzzeichen werden bei Namen normalisiert. Mehrdeutige Aliase werden
abgelehnt. Zusätzliche Apps und Aliase werden pro Fernseher in den Optionen
von Samsung Local gepflegt; Homeintent muss dafür nicht geändert werden.

Bekannte Namen sind unter anderem `netflix`, `prime`, `amazon prime video`,
`youtube`, `disney plus`, `spotify`, `plex` und `apple tv`. Die hinterlegten
Samsung-IDs sind nur regionale Firmware-Kandidaten. Eine App gilt erst nach
Erkennung, manueller Zuordnung oder erfolgreichem Test als für das konkrete
Gerät belegt.

## Einschalten und App starten

Mit `turn_on: true` prüft Samsung Local zuerst den lokalen TV-Endpunkt. Ist er
nicht bereit, wird ausschließlich die für diesen Fernseher konfigurierte
Wake-on-LAN-Adresse verwendet. Danach wartet die Integration bis zum
Power-on-Zeitlimit auf eine echte REST-Antwort und eine funktionierende
Tizen-WebSocket-Verbindung. Erst dann wird ein App-Startverfahren ausgeführt.
Ein gesendetes Magic Packet allein erzeugt keinen erfolgreichen Zustand.

Je nach Firmware kann Samsung Local unterscheiden zwischen „Befehl gesendet“,
„App-Endpunkt bestätigt“ und „App als aktiv erkannt“. Fehlt der lokale
Status-Endpunkt, ist eine erfolgreiche Übertragung möglich, die Aktivierung
aber nicht verifizierbar. Dies wird in den redigierten Diagnosen ausgewiesen.

## Aktionsbeispiele

```yaml
# Netflix im Schlafzimmer
action: samsung_local.launch_app
target:
  entity_id: media_player.schlafzimmer_tv
data:
  app: netflix
  turn_on: true

# Prime Video im Wohnzimmer
action: samsung_local.launch_app
target:
  entity_id: media_player.wohnzimmer_tv
data:
  app: amazon prime
  turn_on: true

# YouTube über den Standard-Media-Player-Pfad
action: media_player.play_media
target:
  entity_id: media_player.schlafzimmer_tv
data:
  media_content_type: app
  media_content_id: youtube

# Erkannte/manuell konfigurierte App aus der Quellenliste
action: media_player.select_source
target:
  entity_id: media_player.schlafzimmer_tv
data:
  source: Netflix

# Fernseher ausschalten
action: media_player.turn_off
target:
  entity_id: media_player.schlafzimmer_tv

# Lautstärke ändern
action: media_player.volume_up
target:
  entity_id: media_player.wohnzimmer_tv

# Home-Taste senden
action: remote.send_command
target:
  entity_id: remote.schlafzimmer_tv
data:
  command: KEY_HOME
```

Homeintent sollte bevorzugt die Standardaktionen `media_player.turn_on`,
`turn_off`, `volume_up`, `volume_down`, `volume_mute`, `media_play`,
`media_pause`, `select_source`, `play_media` und `remote.send_command`
verwenden. Nur der benannte App-Start benötigt die ergänzende Aktion
`samsung_local.launch_app`.

## Fehlervertrag

- kein Samsung-Local-TV im Target: Validierungsfehler;
- unbekannter, deaktivierter oder mehrdeutiger App-Name: Befehlsfehler;
- Wake-on-LAN nicht eingerichtet: Funktion nicht unterstützt;
- TV bis zum Zeitlimit nicht bereit: Verbindungsfehler;
- alle konfigurierten lokalen Startverfahren abgelehnt: App-Startfehler.

Homeintent sollte diese Fehler melden und denselben Schreibbefehl nicht blind
wiederholen. Ein neues App-Mapping wird ausschließlich in Samsung Local
ergänzt; die Sprachlogik übergibt weiterhin nur Alias und Ziel-Entity.
