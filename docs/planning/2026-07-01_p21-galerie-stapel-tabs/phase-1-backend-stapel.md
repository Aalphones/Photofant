# Phase 1 — Backend: Stapel-Datenmodell & Query (Fotos + Gesichter)

**Tier:** heikel
**Status:** complete

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

- [x] `GET /api/assets` (Fotos-Tab) listet **jede** `version`-Zeile (Editor-Dialog-Edits,
  `instance_id` gesetzt) und **jedes** `original_id`-Kind-Asset (ComfyUI-Edits) als
  eigenständigen Eintrag neben dem Original — kein Kollabieren, keine Aggregation
- [x] Jeder Eintrag hat `stack_size` (Gruppengröße) und `stack_group_id`
- [x] Sortierung nach Datum nutzt weiterhin das **eigene** `created_at` jedes Eintrags
  (kein Gruppen-Aggregat-Datum — dieses Konzept entfällt gegenüber der Vorfassung)
- [x] Version-Pseudo-Einträge liefern Tags/Captions/Faces/Person **des Original-Assets**
  (sie haben keine eigenen — Editor-Dialog-Edits sind dieselbe Bild-Identität, nur
  anders gerendert); `original_id`-Kind-Assets liefern ihre **eigenen** (haben sie schon)
- [x] `GET /api/faces` liefert dieselbe Logik für Face-Edit-Gruppen (über `version.face_id`)
- [x] Thumbnail-Auslieferung für einen Version-Eintrag zeigt das Bild dieser Version,
  nicht das des Original-Assets (`/api/versions/{version_id}/thumbnail`, Frontend wählt
  per `kind`/`version_id`)
- [x] Bestehende Filter (Person, Tags, Quelle, Favorit, Suche) funktionieren weiterhin
  korrekt — Filter auf Tags/Caption/Quelle greifen bei Version-Pseudo-Einträgen über
  das Original-Asset (siehe oben), bei `original_id`-Kindern über sich selbst
- [x] Cross-Person-Wanderung eines Edits: befundet **und** gebaut (ADR-013 — ComfyUI-Edit
  wird eigenes Asset, durchläuft die normale Clustering-Pipeline)

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

- [x] Gruppierungs-Hilfsfunktionen `_stack_roots` (löst `original_id`-Kette pro Asset auf,
  bounded depth 5) + `_stack_sizes_for_roots` (Mitgliederzahl: Root + `original_id`-Kinder +
  alle ihre `version`-Zeilen) in `assets.py`
- [x] `list_assets`: `_version_candidates_query` liefert `version`-Zeilen (nur `instance_id`
  gesetzt) für Instanzen, die die bestehende gefilterte Asset-Query bereits passieren —
  kein eigener Filter-Code nötig, Version erbt die Filter über die geteilte Instance-Menge.
  Merge-Strategie statt UNION: Top `page*page_size` je Teilstream (Assets, Versionen)
  sortiert holen, in Python mergen, exakte Seite slicen — korrekt, weil kein Kandidat
  außerhalb der Top-`fetch_limit` seines eigenen Streams vor der angefragten Seite landen
  kann. Semantic-Search-Modus: beide Streams komplett laden (wie schon vor dieser Änderung
  für Assets), Version-Score = Score des Original-Assets.
- [x] Filter greifen bei Version-Pseudo-Einträgen automatisch über das Original (s.o.)
- [x] `AssetDto` erweitert: `kind`, `version_id`, `stack_size`, `stack_group_id`
- [x] Thumbnail-Routing: bestehender Endpunkt `/api/versions/{version_id}/thumbnail`
  (`edit_sessions.py`) wiederverwendet — kein neuer Endpunkt nötig, Frontend wählt anhand
  `kind`/`version_id` (Phase 2/4)

### Faces-Äquivalent

- [x] `api/faces.py`: gleiche Merge-Logik über `version.face_id`, `FaceGalleryItemDto` um
  `kind`, `version_id`, `stack_size`, `stack_group_id` erweitert. Sortierung auf
  `Face.created_at` umgestellt (vorher `Face.id.desc()`) — nötig, um Face- und
  Version-Einträge chronologisch zu mergen; kein Test hing an der alten Reihenfolge.

### Performance

- [x] Index-Check: `ix_version_instance_id`, `ix_version_face_id` bereits vorhanden;
  `asset.original_id` hatte **keinen** Index — ergänzt via Migration `0023` +
  `db/models.py` (`index=True`), Upgrade/Downgrade getestet.
- [x] Merge-Strategie holt je Teilquery nur `page*page_size` Zeilen sortiert von der DB
  (kein Full-Table-Fetch) — einzige Ausnahme: Semantic-Search-Modus lädt beide Streams
  komplett, das war schon vor dieser Änderung so (Score-Sortierung lässt sich nicht auf
  SQL-Ebene vorab limitieren).

---

## Report-Back

**Abweichung vom ursprünglichen Plan:** Die Untersuchung ergab, dass die im Kontrakt
angenommene automatische Cross-Person-Wanderung für ComfyUI-Edits nirgends existierte
(ComfyUI-Default-Import legte immer eine `Version` an, nie ein Asset — siehe README-
Korrektur + [ADR-013](../../decisions/013-comfyui-edit-als-asset.md)). Das musste erst
gebaut werden, bevor der eigentliche Query-Umbau Sinn ergab — dadurch deutlich größerer
Scope als geplant (ADR + Import-Pipeline-Umbau + Query-Umbau in einer Phase).

**Vereinfachung, bewusst:** `original_id`-Ketten werden nur single-hop gezählt
(`_stack_sizes_for_roots`) — ein Edit-eines-Edits (zweite Ebene) würde nicht korrekt
mitgezählt. Für P21s flaches Stapel-Modell (Original + direkte Edits) ausreichend;
`_stack_roots` selbst löst die Kette zwar bounded-rekursiv (Tiefe 5) für die
Gruppen-Identität auf, die Größen-Zählung aber nicht — dokumentierter Kompromiss, kein Bug.

**Getestet:** Bestehende Tests grün (12 vorbestehende, unabhängige Fails — `job_version_inputs`-
Signaturdrift aus einer früheren Phase + `test_caption_config`, identisch auf `master`
reproduziert). Neue Query-Logik selbst hat keine automatisierten Tests (private-Profil,
keine neuen Specs) — manuell mit einer In-Memory-SQLite gegen Root+Version+ComfyUI-Kind
sowie Face+Version-Stapel smoke-getestet (korrekte `stack_size`/`stack_group_id`).

**Follow-up für Phase 2+:** Frontend muss `kind`/`version_id` auswerten, um die richtige
Thumbnail-URL zu wählen (`/api/assets/{id}/thumbnail` vs. `/api/versions/{version_id}/thumbnail`).
