# Sicherheit

## Vertrauensmodell

Samsung Local spricht nur die im Config Entry gespeicherte lokale Adresse an.
Discovery prüft bekannte Endpunkte eines einzelnen Hosts. Unbekannte OCF-
Ressourcen sind Diagnosematerial, keine Schreib-API.

## Secrets

TV-Token, private Schlüssel und PSKs werden weder geloggt noch in Diagnosen
ausgegeben. Sie liegen im geschützten Home-Assistant-Config-Entry und damit in
Home-Assistant-Backups. Das Repository ignoriert `*.pem` und `*.key`.

## Zertifikate

Der optionale automatische Setupweg liest eine öffentliche UUID aus einem
Samsung-Gateway-Zertifikat. Weil dessen Kette nicht normal über Web PKI
verifizierbar ist, wird nur in dieser kleinen Funktion die Serverprüfung
deaktiviert; es werden keine Secrets gesendet. Für strikte WAN-freie
Ersteinrichtung ist die UUID manuell zu importieren.

DTLS wird durch `smartthings-local` authentifiziert. Samsung Local deaktiviert
dessen Serverprüfung nicht global und übernimmt kein Geräte-Ownership.

## Legacy-Risiko

Einige alte Geräte erzwingen TLS 1.0 und ein lokal nicht verifizierbares
Serverzertifikat. Diese Ausnahme existiert nur in `LegacyApplianceAdapter`,
der seinerseits ein Client-Zertifikat und Token sendet. Unbekannte Familien
werden abgelehnt. Ein separates VLAN ist für solche Altgeräte sinnvoll.

## Sichere Befehle

- Werte werden gegen Live-Optionslisten/Bounds geprüft;
- Start/Pause verlangen Smart Control und gültigen Betriebszustand;
- Stop darf als sichere Richtung auch ohne Smart Control versucht werden;
- Writes werden nach Transportfehler nie automatisch wiederholt;
- bestätigter Zustand wird erst nach der nächsten Geräteantwort geändert;
- keine Tür-/Kindersicherungsumgehung, kein generischer Raw-Write-Service.

Sicherheitsmeldungen bitte privat an den späteren Repository-Maintainer senden;
keine echten Credentials oder Identifikatoren in öffentliche Issues stellen.

