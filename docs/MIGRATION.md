# Migration von SmartThings

Samsung Local löscht oder verändert keine SmartThings-Integration und keine
Automation. Migriere parallel und schrittweise.

1. SmartThings unverändert lassen.
2. Samsung Local hinzufügen und Hardwaretests mit WAN noch offen durchführen.
3. Zustände mehrerer Zyklen/Standby-Phasen vergleichen.
4. Für jede Automation prüfen, welche lokale Entity real vorhanden ist.
5. Automation duplizieren, in der Kopie Entity-ID oder Trigger ersetzen.
6. Kopie testen; erst dann alte Automation deaktivieren.
7. Mindestens einige Tage beobachten, inklusive HA- und Geräteneustart.
8. SmartThings nur manuell entfernen, falls es danach wirklich nicht mehr
   benötigt wird. Bei Appliances kann das Entfernen aus SmartThings die
   WLAN-/Geräteregistrierung beeinflussen; im Zweifel registriert lassen.

Das Abschlussereignis kann einen bisherigen Cloud-State-Trigger ersetzen:

```yaml
triggers:
  - trigger: event
    event_type: samsung_local_program_finished
```

Für Entity-IDs, die andere Dashboards/Automationen referenzieren, kann die neue
Samsung-Local-Entity nach erfolgreichem Test in der Entity Registry auf den
alten, nun freien Namen umbenannt werden. Niemals zwei aktive Entities mit
derselben ID erzwingen.

Rückweg: neue Automationen deaktivieren und alte wieder aktivieren. Da Samsung
Local nichts gelöscht hat, ist dafür keine Wiederherstellung nötig.

