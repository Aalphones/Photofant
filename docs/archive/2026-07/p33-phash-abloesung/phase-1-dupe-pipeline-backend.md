# Phase 1 — Dupe-Pipeline Backend

**Komplexität:** standard · **Status:** complete

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

- [x] **`embedding_job.py` — Post-Embedding-Dupe-Check:** In `_run_embedding` nach `upsert_embedding`/Commit, wenn `settings["dupe_clip_enabled"]`: `vector_index.search(session, embedding, limit=settings["dupe_search_limit"])`; Treffer mit `similarity >= 1 - settings["dupe_clip_threshold"]` und `asset_id != self` → `ReviewItem(type="dupe_candidate", asset_a_id=min, asset_b_id=max, clip_distance=1-similarity)` per `sqlite_insert(...).on_conflict_do_nothing()` (Muster: heutiger Block in `import_job.py` Z. 107–114). Eigener try/except wie dort — ein Fehler im Dupe-Check darf das Embedding-Ergebnis nicht zurückrollen.
- [x] **`dupe_scan_job.py`:** pHash-Zweig entfernen — `_compare_chunk`, `_COMPARISON_CHUNK`, `phash_enabled`-Read, pHash-Query, pHash-Progress-Anteil (CLIP-Progress dann 0→0.9), Import von `hamming_distance`. `_PairMatch.phash_distance` entfernen (Insert-Tupel wird `(a, b, clip_distance)`); `_insert_pairs` entsprechend verschlanken.
- [x] **`import_job.py`:** pHash-Block (compute_phash, find_similar, ReviewItem-Inserts, zugehöriger try/except) komplett raus; Import von `media.phash` raus. Rückgabewert/Commit-Struktur unverändert.
- [x] **`comfyui/importer.py`:** analoger Block raus (compute_phash/find_similar/Inserts + Import).
- [x] **`rerun_job.py`:** `_run_phash` + Dispatch-Aufruf + Importe raus; prüfen, ob `_STEP_FLAGS` einen phash-Eintrag hat (dann mit entfernen). (`_STEP_FLAGS` hatte keinen phash-Eintrag — nichts zu tun.)
- [x] **`api/classify.py`:** `"phash"` aus dem `ClassifyStep`-Literal.
- [x] **`api/duplicates.py`:** pHash-Pairwise-Schleife raus; `DupePairDto`-Felder laut Kontrakt; `triggered_by` raus; `similarity_pct = clip_similarity_pct`; Request-Modell: `threshold` raus; Sortierung nach `clip_distance`.
- [x] **`api/review.py`:** `_to_pair_dto` ohne phash/triggered_by; Ordering auf `ReviewItem.clip_distance` statt `phash_distance`; im Ähnliche-Assets-Endpoint den `find_similar`-Zweig + `dupe_phash_enabled`-Read raus; `SimilarAssetDto.phash_distance` raus; `_SimilarMatch` verschlanken; Import von `media.phash` raus. Zusätzlich: `list_dupe_pairs` blendet Alt-Kandidaten mit `clip_distance IS NULL` aus (Übergangsfall, siehe FINDINGS → Phase 4).
- [x] **`settings.py`:** `dupe_phash_enabled` aus Dataclass/Defaults/`_EXPECTED_TYPES` entfernt; `dupe_search_limit: int = 20` neu (alle drei Stellen). `dupe_threshold` bewusst **nicht** entfernt (Abweichung von AK 4, siehe FINDINGS → Phase 2: `api/collections.py` liest ihn noch, Phase 2 macht den finalen Cut). Keine Migration nötig (Loader deep-merged, Alt-Keys in bestehender Datei sind harmlos — verifiziert).
- [x] **Tests:** `backend/tests/` nach `phash`/`dupe` durchsucht — keine bestehenden Tests decken dupe_scan/duplicates/review/settings direkt ab, nichts anzupassen. `uv run pytest` (189 passed, 13 vorbestehende Fails unberührt, per Stash-Vergleich verifiziert) + `uv run ruff check .` grün für alle Phase-1-Dateien.
- [x] **Doc-Update:** `docs/routes.md` — `/api/duplicates/search`-Body, `ClassifyStep`-Werte, `DupePairDto`/`PersonDupePair`/`SimilarAssetDto` und die Sortierbeschreibung nachgezogen.

## Report-Back

**Abweichung vom Plan:** `dupe_threshold` bleibt in `settings.py` erhalten (User-Entscheidung während der Umsetzung) — `api/collections.py`s Trainingsset-Duplikatsuche (Phase 2) liest ihn noch; ein sofortiges Entfernen hätte diesen Endpoint mit `KeyError` crashen lassen. Phase 2 entfernt den Key final, sobald `collections.py` auf CLIP umgestellt ist (siehe FINDINGS.md).

**Zusätzlich gefunden & mitgelöst:** `list_dupe_pairs` blendet unresolved Alt-Kandidaten mit `clip_distance IS NULL` aus (reine pHash-Funde aus der Zeit vor diesem Umbau) — sonst hätte die non-null-`clip_distance`-Vorgabe aus dem Kontrakt beim Serialisieren mit `HTTPException` reagiert. `resolve_dupe` wirft in diesem Randfall bewusst `409` statt eines Pydantic-Crashs. Phase 4 räumt diese Alt-Kandidaten endgültig weg.

**Nicht angetastet:** `backend/photofant/media/orientation_overwrite.py` (Face/Asset-pHash-Refresh nach Crop-Overwrite) — gehört laut Plan zu Phase 2, dort bereits in der Checkliste erfasst.
