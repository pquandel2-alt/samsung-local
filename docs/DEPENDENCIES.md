# Abhängigkeiten

## Laufzeit

| Paket | Pin | Lizenz | Zweck | Entscheidung |
|---|---:|---|---|---|
| `smartthings-local` | 0.1.24 | MIT | CoAP/DTLS, X.509/PSK, Observe, Probing | veröffentlichte Bibliothek statt kopiertem Protokoll |
| `samsungtvws[async]` | 3.0.6 | LGPL-3.0 | Tizen WebSocket/REST/Pairing/Apps | unverändert dynamisch gelinkt |
| `cbor2` | 5.9.0 | MIT | OCF-CBOR | direkter, sicherheitsaktualisierter Pin |
| `wakeonlan` | 3.3.0 | MIT | Magic Packets an konfigurierbares IPv4-Ziel | Home-Assistant-kompatibler Pin statt eigener Paketlogik |

Transitive Kryptografie (`cryptography`, `pyOpenSSL`) wird durch
`smartthings-local` verlangt und in Home Assistant zentral auf kompatible
Versionen aufgelöst. Es gibt keine Runtime-Abhängigkeit auf LocalThings,
SmartThings Cloud, MQTT oder einen externen Dienst.

## Sicherheitsscan

Am 12.10.2026 wurde `pip-audit` gegen die lokale Testumgebung ausgeführt.
Der erste Lauf fand für `cbor2==5.7.1` `PYSEC-2025-90` und
`PYSEC-2026-2123`; die Version wurde daraufhin auf 5.9.0 angehoben. Nach dem
Upgrade und der Aktualisierung des nur zur Entwicklung genutzten `pip` meldete
der zweite Lauf: **No known vulnerabilities found**.

Dieser erfolgreiche Lauf betrifft den Samsung-Local-Runtime-/Unit-Test-Satz.
Der separat installierte Home-Assistant-Harness ist durch
`pytest-homeassistant-custom-component==0.13.338` auf HA 2026.6.2 und dessen
damalige transitive Versionen festgelegt. Ein Audit dieser isolierten
Entwicklungsumgebung meldet inzwischen Advisories unter anderem für den alten
HA-Core-Pin, `aiohttp`, `cryptography`, Pillow und PyJWT. Diese Pakete werden
nicht durch `manifest.json` auf jene alten Versionen festgelegt; Anwender
sollen eine aktuelle, unterstützte Home-Assistant-Version verwenden.

Ein Audit ist zeitgebunden und beweist keine Abwesenheit unbekannter Fehler.
Der CI-Workflow wiederholt ihn bei Push, Pull Request und wöchentlich.

`wakeonlan==3.3.0` wurde für diese Änderung ergänzt. Es entspricht dem von
Home Assistant verwendeten Pin, führt keine Discovery
und keinen externen Zugriff aus, sondern sendet ausschließlich das Magic
Packet an die vom Benutzer gewählte lokale Zieladresse und UDP-Port.

## Entwicklung

`pytest`, `pytest-asyncio`, `ruff`, `mypy`,
`pytest-homeassistant-custom-component`, Hassfest und HACS validation laufen
nicht auf dem Home-Assistant-Gerät als Teil der Integration.

## Lizenzkonformität

Der Repository-Code steht unter MIT. MIT-Abhängigkeiten sind in
`THIRD_PARTY_NOTICES.md` genannt. `samsungtvws` bleibt eine unmodifizierte,
austauschbare LGPL-3.0-Bibliothek; ihr Quellrepository und ihre Lizenz sind
dokumentiert. Samsung Local kopiert keinen Bibliotheksquellcode.
