# Veröffentlichung

Der lokale Stand erzeugt keinen Release und führt keinen Push aus. Vor dem
ersten öffentlichen Beta-Release sind folgende eigentümerabhängigen Angaben
zu setzen:

1. GitHub-Organisation oder Benutzerkonto und Repository `samsung-local`
   anlegen.
2. Die Platzhalter-URLs unter `documentation` und `issue_tracker` in
   `custom_components/samsung_local/manifest.json` auf dieses Repository
   ändern.
3. Mindestens einen realen GitHub-Handle als `codeowners` eintragen.
4. Git-Remote setzen, Branch Protection für `main` aktivieren und den
   `develop`-Branch über einen Pull Request einbringen.
5. CI, Hassfest, HACS validation und Dependency Audit erfolgreich abwarten.
6. Hardwarestatus weiterhin höchstens `implemented_unverified` nennen, bis
   die dokumentierten realen Prüfungen bestanden sind.
7. Den manuellen Workflow „Prepare release artifact“ mit der Manifest-Version
   ausführen und das Artefakt prüfen. Er veröffentlicht absichtlich keinen Tag
   und kein Release.

Vor einer stabilen Version müssen die Stable-Gates aus `ROADMAP.md` erfüllt
sein. Versionsnummern folgen Semantic Versioning; `0.1.0-beta.1` ist die erste
vorgesehene Testversion.
