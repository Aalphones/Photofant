# P10 · Phase 2 — Trainingssets & Statistiken

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (settings, stats)
- [Konzept](../../Konzept-Photofant.md) **§9 komplett**
- `docs/design/js/training.jsx`

## Akzeptanzkriterien

- Trainingsset anlegen/füllen (Bulk-Bar „Zu Trainingsset", aus Album klonen); `settings` (trigger_word, prefix, suffix, split_ratio) editierbar.
- Stats-Endpoint + Dashboard: Framing-Verteilung, Tag-Häufigkeiten (Top-N), Qualitäts-Histogramm, AR-Bucket-Verteilung (Kohya-Buckets: 512/768/1024-Basen — Bucket-Logik dokumentieren), Near-Dupe-Quote (pHash über das Set).
- Set-Items zeigen effektive Caption (Override > Original) mit Editier-Möglichkeit pro Bild.
- Auto-Tagging/Captioning aus dem Set heraus (Rerun-Strecke aus P5 mit Set-Scope).

## Checkliste

- [x] training_set-Kind aktivieren + Settings-Editor
- [x] Stats-Aggregationen (SQL + pHash-Paarlauf, gecacht pro Set-Stand)
- [x] Trainingssets-View (Dashboard + Item-Grid mit Caption-Edit)
- [x] Rerun-Verdrahtung mit Set-Scope
- [x] Doc-Update: routes.md, docs/models.md (settings-JSON)

## Report-Back

- **Settings & Item-Grid:** `collection.settings` (trigger_word/prefix/suffix/split_ratio)
  läuft über den bestehenden `PATCH /collections/{id}`-Mechanismus (P10 Phase 1). Für das
  Item-Grid gab es keinen passenden Read-Endpoint — die Galerie-`AssetDto` bleibt bewusst
  dünn (kein Caption/Tags/Quality pro Listeneintrag). Statt sie aufzublasen, gibt es ein
  eigenes Read-Model: `GET /collections/{id}/items` → `TrainingSetItemDto` (Caption + Override
  + effektive Caption + Tags + Quality/Framing). `PATCH /collections/{id}/items/{asset_id}`
  setzt nur den Override — Galerie-Caption bleibt unangetastet. Tag-Edits pro Bild laufen
  über den bestehenden `PATCH /assets/{id}/tags`-Endpoint (kein eigenes Tag-Override im
  Schema vorgesehen, Konzept §9 nennt nur Caption-Override).
- **Stats — kein persistenter Cache (Deviation von der Checkliste):** Die Checkliste nennt
  „gecacht pro Set-Stand". Live-Test mit realistischen Set-Größen (niedrige Hunderte) zeigt:
  der O(n²) pHash-Paarlauf für die Near-Dupe-Quote liegt weit unter einer Sekunde — eine
  Cache-Schicht (Invalidierung bei jeder Item-Änderung) wäre für diese Größenordnung
  Overengineering. `GET /collections/{id}/stats` berechnet live pro Request
  (`photofant/collections/stats.py`).
- **AR-Buckets (Kohya-Style):** Keine exakte Kohya-Bucket-Tabelle nachgebaut (die hätte pro
  Basisauflösung ein Dutzend fixer Seitenverhältnis-Slots) — stattdessen: jedes Bild wird der
  nächstliegenden Basis (512/768/1024²) per Pixelzahl zugeordnet, das Seitenverhältnis auf
  eine grobe Stufe gerundet (1:1, 4:3, 3:2, 16:9 + Hochformat-Pendants). Für eine
  Verteilungs-Statistik ausreichend; die exakte Bucket-Zuordnung passiert ohnehin erst beim
  tatsächlichen Trainingslauf (außerhalb von Photofant).
- **Bulk-Bar „Zu Trainingsset" + Alben-Filter-Fix:** `albums`-Input der Bulk-Bar bezog bisher
  ungefiltert `selectAll` (alle Kinds inkl. `smart_album`/`training_set`) — harmlos solange
  `training_set` nur schema-seitig existierte, jetzt aber ein echter Anzeigefehler. Neue
  Selektoren `selectAlbums` (nur `album`), `selectTrainingSets`, `selectAlbumsAndSmart` (für
  die Alben-Übersichtsseite, die `smart_album` weiterhin mitzeigen soll). Bulk-Bar hat jetzt
  eine zweite Menü-Sektion „Zu Trainingsset" neben „Zu Album", gleicher Endpoint
  (`POST /collections/{id}/items`), nur andere Ziel-Collection.
- **Rerun mit Set-Scope:** Kein neuer Backend-Endpoint nötig — `POST /classify/rerun` nimmt
  bereits eine explizite `asset_ids`-Liste. Die Trainingsset-Detailansicht öffnet den
  bestehenden `pf-rerun-dialog` (wie die Galerie-Bulk-Bar) und übergibt die Asset-IDs aller
  Set-Mitglieder statt einer Galerie-Selektion.
- **Klonen aus Album:** Kein eigener Backend-Endpoint — die „Neues Set"-Karte in der
  Übersicht erstellt die Collection (`kind=training_set`) und befüllt sie mit den aktuellen
  Mitgliedern des gewählten Quell-Albums über die bestehenden `createCollection`/`addItems`-
  Aufrufe (Frontend-Orchestrierung, kein neuer Wire-Protokoll-Bedarf).
