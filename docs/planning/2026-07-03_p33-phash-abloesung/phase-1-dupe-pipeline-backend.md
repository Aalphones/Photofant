# Phase 1 — Dupe-Pipeline Backend

**Komplexität:** standard · **Status:** pending

## Kontext (vor Arbeitsbeginn lesen)

- `README.md` dieses Plans (Kontrakt-Sektion!)
- `backend/photofant/jobs/embedding_job.py` — hier dockt der neue Check an
- `backend/photofant/db/vector_index.py` — `search(session, query_embedding, limit)` → `list[(asset_id, cosine_similarity)]`
- `backend/photofant/jobs/dupe_scan_job.py` — pHash-Zweig fällt, CLIP-Zweig bleibt
- `backend/photofant/jobs/import_job.py` (Z. ~97–125), `backend/photofant/comfyui/importer.py` (Z. ~197–216), `backend/photofant/jobs/rerun_job.py` (`_run_phash`) — die drei Import-Zeit-Checks, die ersatzlos fallen
- `backend/photofant/api/classify.py` — `ClassifyStep`-Literal
- `backend/photofant/api/duplicates.py`, `backend/photofant/api/review.py` — DTOs/Sortierung
- `backend/photofant/settings.py` — Keys laut Kontrakt
- `backend/photofant/db/models.py` — `ReviewItem` + Unique-Index `uq_review_item_pair` (Idempotenz-Anker)
- `docs/conventions/python.md`

## AK

1. Nach jedem erfolgreichen Embedding-Lauf werden Dupe-Kandidaten via sqlite-vec gesucht und als `dupe_candidate`-ReviewItems persistiert (idempotent).
2. Dupe-Scan-Job, `/api/duplicates/*` und `/api/review/*` arbeiten CLIP-only; keine pHash-Felder mehr in Responses.
3. `"phash"` ist kein Rerun-Step mehr; Import/ComfyUI-Import/Rerun berechnen kein pHash mehr (die Spalten-Schreibvorgänge auf `Asset.phash` entfallen — die Spalte selbst fällt erst in Phase 4).
4. Settings: `dupe_threshold` + `dupe_phash_enabled` raus, `dupe_search_limit` (int, 20) neu; `uv run ruff check .` grün, betroffene Tests angepasst und grün.

## Checkliste

- [ ] **`embedding_job.py` — Post-Embedding-Dupe-Check:** In `_run_embedding` nach `upsert_embedding`/Commit, wenn `settings["dupe_clip_enabled"]`: `vector_index.search(session, embedding, limit=settings["dupe_search_limit"])`; Treffer mit `similarity >= 1 - settings["dupe_clip_threshold"]` und `asset_id != self` → `ReviewItem(type="dupe_candidate", asset_a_id=min, asset_b_id=max, clip_distance=1-similarity)` per `sqlite_insert(...).on_conflict_do_nothing()` (Muster: heutiger Block in `import_job.py` Z. 107–114). Eigener try/except wie dort — ein Fehler im Dupe-Check darf das Embedding-Ergebnis nicht zurückrollen.
- [ ] **`dupe_scan_job.py`:** pHash-Zweig entfernen — `_compare_chunk`, `_COMPARISON_CHUNK`, `phash_enabled`-Read, pHash-Query, pHash-Progress-Anteil (CLIP-Progress dann 0→0.9), Import von `hamming_distance`. `_PairMatch.phash_distance` entfernen (Insert-Tupel wird `(a, b, clip_distance)`); `_insert_pairs` entsprechend verschlanken.
- [ ] **`import_job.py`:** pHash-Block (compute_phash, find_similar, ReviewItem-Inserts, zugehöriger try/except) komplett raus; Import von `media.phash` raus. Rückgabewert/Commit-Struktur unverändert.
- [ ] **`comfyui/importer.py`:** analoger Block raus (compute_phash/find_similar/Inserts + Import).
- [ ] **`rerun_job.py`:** `_run_phash` + Dispatch-Aufruf + Importe raus; prüfen, ob `_STEP_FLAGS` einen phash-Eintrag hat (dann mit entfernen).
- [ ] **`api/classify.py`:** `"phash"` aus dem `ClassifyStep`-Literal.
- [ ] **`api/duplicates.py`:** pHash-Pairwise-Schleife raus; `DupePairDto`-Felder laut Kontrakt; `triggered_by` raus; `similarity_pct = clip_similarity_pct`; Request-Modell: `threshold` raus; Sortierung nach `clip_distance`.
- [ ] **`api/review.py`:** `_to_pair_dto` ohne phash/triggered_by; Ordering (Z. ~178–183) auf `ReviewItem.clip_distance` statt `phash_distance`; im Ähnliche-Assets-Endpoint den `find_similar`-Zweig + `dupe_phash_enabled`-Read raus; `SimilarAssetDto.phash_distance` raus; `_SimilarMatch` verschlanken; Import von `media.phash` raus.
- [ ] **`settings.py`:** `dupe_threshold`, `dupe_phash_enabled` aus Dataclass/Defaults/`_EXPECTED_TYPES`; `dupe_search_limit: int = 20` neu (alle drei Stellen). Keine Migration nötig (Loader deep-merged, Alt-Keys in bestehender Datei sind harmlos — verifiziert).
- [ ] **Tests:** bestehende Backend-Tests zu dupe_scan/duplicates/review/settings anpassen (`backend/tests/` nach `phash`/`dupe` greppen); danach `uv run pytest` für die betroffenen Module + `uv run ruff check .`.
- [ ] **Doc-Update:** `docs/routes.md` — `/api/duplicates/search`-Body und `ClassifyStep`-Werte nachziehen.

## Report-Back
