# Veröffentlichung

Zielrepository: `https://github.com/pquandel2-alt/samsung-local`.

Stand der ersten öffentlichen Beta:

1. Repository, Remote sowie die Branches `main` und `develop` sind angelegt.
2. Quality, HA-Integrationstests, Hassfest, HACS validation und Dependency
   Audit sind auf GitHub erfolgreich durchgelaufen.
3. `main` sollte vor weiteren Entwicklungsänderungen mit Branch Protection
   und verpflichtenden Pull Requests geschützt werden.
4. Hardwarestatus weiterhin höchstens `implemented_unverified` nennen, bis
   die dokumentierten realen Prüfungen bestanden sind.
5. Der manuelle Workflow „Prepare release artifact“ bleibt für spätere
   Release-Kandidaten verfügbar und veröffentlicht absichtlich nicht selbst.

Vor einer stabilen Version müssen die Stable-Gates aus `ROADMAP.md` erfüllt
sein. Versionsnummern folgen Semantic Versioning; `0.1.0-beta.1` ist die erste
vorgesehene Testversion.
