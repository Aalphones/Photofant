# Phase 2 — Import-Pipeline Auto-Detection

## Kontext (vor Implementierung lesen)

- `docs/planning/2026-06-19_duplikaterkennung/README.md` — Kontrakt: API, DB, Typen
- `backend/photofant/jobs/import_job.py` — `_import_single`: hier läuft die Erweiterung an
- `backend/photofant/media/phash.py` — `compute_phash`, `hamming_distance` (Phase 1)
- `backend/photofant/db/models.py` — `Asset.phash`, `ReviewItem` (Phase 1)
- `backend/photofant/settings.py` — `dupe_threshold` (Phase 1)

## Akzeptanzkriterien

1. `_import_single` berechnet nach dem Kopieren der Datei den pHash und speichert ihn auf `asset.phash`.
2. Nach dem DB-Commit: alle bestehenden Assets mit pHash werden gegen den neuen pHash verglichen (Hamming ≤ `dupe_threshold`).
3. Für jeden Treffer wird ein `review_item` vom Typ `dupe_candidate` angelegt (mit normiertem `asset_a_id < asset_b_id`).
4. Existiert das Paar bereits in `review_item` (Unique-Constraint), wird der Eintrag übersprungen (kein Fehler).
5. Import bleibt nicht-blockierend: ähnliche Bilder werden **trotzdem** importiert — nur zur Entscheidung eingestellt.
6. pHash-Fehler (kaputte Datei, Pillow-Exception) werden geloggt, der Import selbst schlägt nicht fehl.

## Checkliste

### Backend

- [ ] `backend/photofant/media/phash.py` — `find_similar(session, new_phash: int, new_asset_id: int, threshold: int) -> list[tuple[int, int]]` hinzufügen:
  - Lädt alle `(asset.id, asset.phash)` aus DB (WHERE `phash IS NOT NULL AND id != new_asset_id`)
  - Gibt `[(other_asset_id, distance), ...]` für alle Treffer ≤ Threshold zurück
  - Reihenfolge: niedrigste Distanz zuerst
- [ ] `backend/photofant/jobs/import_job.py` — `_import_single` erweitern:
  - Nach `session.commit()`: `phash_val = compute_phash(source_path)`; Fehler loggen + skip wenn Exception
  - `asset.phash = phash_val`; `session.commit()` (separater Commit für pHash — Import-Erfolg nicht rückgängig machen wenn pHash schlägt fehl)
  - `similar = find_similar(session, phash_val, asset.id, settings.dupe_threshold)`
  - Für jeden Treffer: `ReviewItem` anlegen, `on_conflict_do_nothing` (oder try/except IntegrityError)
  - `session.commit()`
- [ ] pHash-Berechnung läuft **nach** dem File-Copy und **nach** dem Asset-Commit — nie davor
- [ ] `settings = load_settings()` einmal lesen, nicht pro Iteration

### Tests

- [ ] `backend/tests/test_import_job.py` (falls vorhanden) — Smoke-Test: Import zweier ähnlicher Bilder → ein `review_item` in DB

### Docs

- [ ] `docs/models.md` `review_item` — Beispiel-Flow in einem Satz ergänzen (optional, wenn noch nicht in Phase 1)

## Report-Back
