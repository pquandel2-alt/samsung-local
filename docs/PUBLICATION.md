# Veröffentlichung

Zielrepository: `https://github.com/pquandel2-alt/samsung-local`.

Für die erste öffentliche Beta gelten folgende Schritte:

1. Repository `samsung-local` unter dem Eigentümer `pquandel2-alt` anlegen.
2. Git-Remote setzen und den geprüften Initialstand auf `main` sowie
   `develop` veröffentlichen. Nachfolgende Änderungen laufen über Pull
   Requests von `develop` nach `main`.
3. CI, Hassfest, HACS validation und Dependency Audit erfolgreich abwarten.
4. Branch Protection für `main` aktivieren, sobald der initiale Stand
   veröffentlicht ist.
5. Hardwarestatus weiterhin höchstens `implemented_unverified` nennen, bis
   die dokumentierten realen Prüfungen bestanden sind.
6. Den manuellen Workflow „Prepare release artifact“ mit der Manifest-Version
   ausführen und das Artefakt prüfen. Er veröffentlicht absichtlich keinen Tag
   und kein Release.

Vor einer stabilen Version müssen die Stable-Gates aus `ROADMAP.md` erfüllt
sein. Versionsnummern folgen Semantic Versioning; `0.1.0-beta.1` ist die erste
vorgesehene Testversion.
