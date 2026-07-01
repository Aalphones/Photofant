# Phase 1 — Backend: Stapel-Datenmodell & Query (Fotos + Gesichter)

**Tier:** heikel
**Status:** pending

Voraussetzung für alle anderen Phasen. Ersetzt die ursprüngliche Fassung (Dual-Listing
mit Stapel-Kopf + Original-Echo) durch das flache Modell aus der README (Korrektur
2026-07-01): jede Version ist ein eigener, gleichberechtigter Eintrag.

---

## Kontext (was vorher lesen)

- `backend/photofant/api/assets.py` — `_base_query`, `list_assets` (Zeile ~267), `AssetDto`
  (Zeile ~56), `get_asset_thumbnail` (Zeile ~379)
- `backend/photofant/api/faces.py` — bestehende Face-Liste/Query
- `backend/photofant/db/models.py` — `Asset.original_id`, `Version` (XOR `instance_id`/`face_id`,
  `is_current`, `type`), `AssetInstance` (Multi-Instanz-Semantik P7 Phase 3)
- `docs/models.md` — Sektionen `asset`, `asset_instance`, `version`, `face`
- README dieses Plans — Kontrakt-Sektion „Stapel" + Pipeline-Scope-Entscheidung
  (ComfyUI-Edits volle Pipeline, Editor-Dialog-Edits ohne eigene Faces/Captions/Tags)

---

## Abnahme-Kriterien

- [ ] `GET /api/assets` (Fotos-Tab) listet **jede** `version`-Zeile (Editor-Dialog-Edits,
  `instance_id` gesetzt) und **jedes** `original_id`-Kind-Asset (ComfyUI-Edits) als
  eigenständigen Eintrag neben dem Original — kein Kollabieren, keine Aggregation
- [ ] Jeder Eintrag hat `stack_size` (Gruppengröße) und `stack_group_id`
- [ ] Sortierung nach Datum nutzt weiterhin das **eigene** `created_at` jedes Eintrags
  (kein Gruppen-Aggregat-Datum — dieses Konzept entfällt gegenüber der Vorfassung)
- [ ] Version-Pseudo-Einträge liefern Tags/Captions/Faces/Person **des Original-Assets**
  (sie haben keine eigenen — Editor-Dialog-Edits sind dieselbe Bild-Identität, nur
  anders gerendert); `original_id`-Kind-Assets liefern ihre **eigenen** (haben sie schon)
- [ ] `GET /api/faces` liefert dieselbe Logik für Face-Edit-Gruppen (über `version.face_id`)
- [ ] Thumbnail-Auslieferung für einen Version-Eintrag zeigt das Bild dieser Version,
  nicht das des Original-Assets
- [ ] Bestehende Filter (Person, Tags, Quelle, Favorit, Suche) funktionieren weiterhin
  korrekt — Filter auf Tags/Caption/Quelle greifen bei Version-Pseudo-Einträgen über
  das Original-Asset (siehe oben), bei `original_id`-Kindern über sich selbst
- [ ] Cross-Person-Wanderung eines Edits: befund­et **und** falls fehlend gebaut (siehe
  Checkliste „Untersuchung zuerst") — das ist der Kern dieser Phase, nicht nur
  Beiwerk zur Anzeige

---

## Checkliste

### Untersuchung zuerst (Chesterton's Fence — nicht annehmen)

**Ergebnis (2026-07-01, siehe README-Korrektur + ADR-013):**

- `version`-Zeilen (Editor-Dialog-Edits) haben **keine** eigene Gesichtserkennung
  (`face_job.py` läuft nur über `asset_id`) — für sie gibt es und braucht es **keine**
  Umhänge-Logik. Sie bleiben immer im Personen-Ordner ihrer Quelle.
- `original_id`-Kind-Assets liefen bisher **nicht automatisch** durch die Pipeline —
  `import_comfyui_output` legte immer eine `Version` an, nie ein Asset. ADR-013 dreht
  das um: ab jetzt legt der ComfyUI-Default-Import (Upscale/Edit/Inpaint) ein echtes
  Asset mit `original_id` an und durchläuft dieselbe Pipeline wie ein normaler
  Foto-Import (Tags/Caption/Face/Embedding/pHash) — danach greift die bestehende
  Clustering-Materialisierung (P7) normal.
- Eine Gruppe kann Mitglieder aus **beiden** Quellen gleichzeitig haben (mehrere
  `version`-Zeilen UND `original_id`-Kinder) — Gruppierungs-Logik muss beide mergen.

**Neu in dieser Phase (ADR-013-Umsetzung):**

- [x] `comfyui/importer.py::import_comfyui_output` umgebaut: legt jetzt ein vollwertiges
  `Asset` an (`read_meta`, `content_hash`, `ProcessingLedger`, pHash + Dupe-Review),
  `original_id` = Quell-Asset, `AssetInstance` in der Person des Quell-Assets, Datei
  bleibt in `personX/edits/`
- [x] Neue Rückgabe (`ImportedComfyUIAsset`) löst normale Pipeline aus — Aufrufer rufen
  `jobs/import_job.py::enqueue_post_import_pipeline` (neuer public Wrapper um
  `_enqueue_pipeline`)
- [x] Beide Call-Sites umgestellt: `jobs/comfyui_run_job.py::_import_and_cleanup` (Default-
  Endpunkt) + `api/comfyui.py::import_comfyui_result` (manueller Ergebnis-Import)
- [x] `media/person_folders.py::materialize_assignment`: Ziel-Subordner `edits/` statt
  `photos/`, wenn `asset.original_id is not None` (Move- und Copy-Zweig)
- [x] Bestehende `Version`-Zeilen vom Typ `comfyui` bleiben unangetastet — keine Migration
- [x] Bestehende Tests (`test_comfyui_import.py`, `test_comfyui_auto_import.py`) auf neues
  Verhalten umgeschrieben, `pytest`/`ruff` grün (12 vorbestehende Fails aus
  `job_version_inputs`-Drift/`test_caption_config` — unabhängig von dieser Änderung,
  auf `master` identisch reproduziert)

**Noch offen in dieser Phase** (Query-Umbau selbst, s.u.): Gruppierung/`stack_size`/
`stack_group_id` für Fotos + Faces, `AssetDto`-Erweiterung, Thumbnail-Routing für
Version-Pseudo-Einträge, Performance-Check.

### Query-Umbau — Fotos

- [ ] Gruppierungs-Hilfsfunktion: pro Original alle Gruppenmitglieder ermitteln
  (`version`-Zeilen der zugehörigen `asset_instance` + Assets mit `original_id == asset.id`),
  daraus `stack_size` ableiten (1 + Anzahl Mitglieder)
- [ ] `list_assets`: bestehende Asset-Query bleibt (liefert Original + `original_id`-Kinder
  bereits heute, nur ohne Stapel-Metadaten) — zusätzlich `version`-Zeilen (nur
  `instance_id` gesetzt, nicht `face_id`) als Pseudo-Einträge in dieselbe Ergebnisliste
  einmischen (UNION oder zweiter Query-Pass + Merge vor Pagination)
- [ ] Filter (Tags/Caption/Quelle/Person/Favorit/Suche) müssen bei Version-Pseudo-
  Einträgen über das zugehörige Original-Asset ausgewertet werden — nicht separat
  filterbar, da sie keine eigenen Tags/Captions haben
- [ ] `AssetDto` um `stack_size: number`, `stack_group_id: number | null` erweitern;
  Version-Pseudo-Einträge brauchen ein Unterscheidungsmerkmal (z.B. `kind: 'asset' | 'version'`
  + `version_id` wenn `kind === 'version'`) — Frontend braucht das für den Lightbox-Einstieg
  (Phase 4: „öffne Asset X mit initial gewählter Version Y" statt eigenes Detail-Objekt)
- [ ] `get_asset_thumbnail`: Version-Pseudo-Eintrag löst über `version_id` statt `asset_id`
  auf — bestehende Route für Versionen-Thumbnails prüfen (`VersionDto.thumbnail_url` —
  gibt es dafür schon einen Endpunkt? Falls ja, wiederverwenden statt duplizieren)

### Faces-Äquivalent

- [ ] `api/faces.py`: gleiche Gruppierung + gleiches Merge-Verfahren über `version.face_id`,
  gleiche zwei neuen Felder auf `FaceGalleryItemDto`

### Performance

- [ ] Bei großen Bibliotheken (Tausende Assets): Index-Check auf `version.instance_id`,
  `version.face_id`, `asset.original_id` — vorhanden laut `docs/models.md`? Ergänzen falls nicht.
- [ ] Merge zweier Query-Ergebnisse vor Pagination: im Blick behalten, dass das nicht zu
  einem Full-Table-Scan wird (Critical Rule 5 „UI blockiert nie") — ggf. Sortierung/Limit
  auf SQL-Ebene je Teilquery vor dem Merge anwenden

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
