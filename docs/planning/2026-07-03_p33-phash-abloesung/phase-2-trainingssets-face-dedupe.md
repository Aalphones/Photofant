# Phase 2 — Trainingssets + Face-Dedupe Backend

**Komplexität:** standard · **Status:** complete

## Kontext (vor Arbeitsbeginn lesen)

- `README.md` dieses Plans (Kontrakt-Sektion)
- `backend/photofant/api/collections.py` — `/collections/{id}/duplicates`-Endpoint (Z. ~640–680), `CollectionDupePairDto`, `_DUPE_MAX_THRESHOLD`
- `backend/photofant/collections/stats.py` — `_near_dupe_rate`, `compute_training_set_stats`
- `backend/photofant/jobs/dupe_scan_job.py` — `_compare_chunk_clip` als **Muster** für CLIP-Pairwise (nach Phase 1 CLIP-only)
- `backend/photofant/api/edit_sessions.py` — pHash-Dedupe-Block (Z. ~370–495): `existing_phashes`, `_phash_hamming`, `_PHASH_QUASI_IDENTICAL_THRESHOLD`
- Face-pHash-Schreiber: `backend/photofant/jobs/face_job.py` (`_compute_crop_phash`), `backend/photofant/jobs/face_folder_scan_job.py` (Z. ~92–100), `backend/photofant/api/faces.py` (Z. ~404–412), `backend/photofant/media/orientation_overwrite.py` (Z. 109 Face + Z. 168 Asset)
- `backend/photofant/jobs/clustering_job.py` — `phash_distance=0` bei face_suggestion (Z. ~176)
- `docs/conventions/python.md`

## AK

1. Trainingsset-Dupes-Endpoint vergleicht CLIP-Embeddings (Distanz-Semantik laut Kontrakt), Near-Dupe-Quote in den Stats rechnet auf CLIP mit `training_near_dupe_clip_threshold`.
2. Face-Crop-Dedupe bei Edit-Versionen vergleicht buffalo_l-Embeddings (Cosine ≥ `face_dedupe_similarity_threshold` ⇒ skip) statt pHash.
3. Kein Code schreibt mehr `Asset.phash` oder `Face.phash` (Spalten fallen in Phase 4).
4. Settings: `training_near_dupe_clip_threshold` (0.05) + `face_dedupe_similarity_threshold` (0.9) neu; ruff + betroffene Tests grün.

## Checkliste

- [x] **`api/collections.py` `/duplicates`:** Query lädt `Asset.clip_embedding` statt `Asset.phash` (Filter `clip_embedding.is_not(None)`); Pairwise via numpy-Matmul (Muster `_compare_chunk_clip`: `np.frombuffer(float32)`, Stack, `chunk @ vectors.T`, Distanz = 1 − Similarity); `CollectionDupePairDto.phash_distance` → `clip_distance: float`; `similarity_pct = round((1 - clip_distance) * 100)`; `threshold`-Param + `_DUPE_MAX_THRESHOLD` auf CLIP-Distanz-Semantik (float, Kappung bei 0.5); Default aus `training_near_dupe_clip_threshold`; Sortierung nach `clip_distance` aufsteigend; `hamming_distance`-Import raus.
- [x] **`collections/stats.py`:** `_near_dupe_rate(phashes)` → `_near_dupe_rate(embeddings)` auf CLIP-Basis: Blobs zu float32-Matrix, `matrix @ matrix.T`, Partner = Distanz ≤ `training_near_dupe_clip_threshold`; Query in `compute_training_set_stats` lädt `Asset.clip_embedding` statt `Asset.phash`; `_NEAR_DUPE_THRESHOLD`-Konstante + `hamming_distance`-Import raus. Struktur der `has_partner`-Logik beibehalten (Anteil Bilder mit ≥1 Partner).
- [x] **`api/edit_sessions.py` — Face-Dedupe auf Embeddings:** `existing_phashes` → `existing_embeddings` (Query lädt `Face.embedding` statt `Face.phash`, `np.frombuffer(float32)`); im Detect-Loop den pHash-Berechnungsblock (imagehash) entfernen und stattdessen `face_dict["embedding"]` gegen `existing_embeddings` per Cosine vergleichen (Embeddings sind L2-normalisiert ⇒ Dot-Product); `similarity >= settings["face_dedupe_similarity_threshold"]` ⇒ Crop löschen + skip (Log-Zeile sinngemäß von „pHash-Dedupe" auf „Face-Dedupe" umbenannt — auch die übrigen Log-Präfixe im Block, plus Funktionsname `_run_version_phash_dedupe` → `_run_version_face_dedupe`); `_phash_hamming` + `_PHASH_QUASI_IDENTICAL_THRESHOLD` raus; beim Anlegen der neuen Face-Row das `phash=`-Feld weggelassen.
- [x] **Face-/Asset-pHash-Schreiber entfernen:** `face_job.py` (`_compute_crop_phash` + Aufruf + `phash=`-Arg), `face_folder_scan_job.py` (pHash-Block + `phash=`-Arg), `api/faces.py` (pHash-Block + `phash=`-Arg), `orientation_overwrite.py` (beide Recompute-Zeilen + Importe von `compute_phash`/`compute_phash_hex`; Docstrings, die `phash` als refreshtes Feld nannten, mitgezogen).
- [x] **`clustering_job.py`:** `phash_distance=0` aus dem `ReviewItem(type="face_suggestion", …)`-Konstruktor raus (Spalte ist nullable).
- [x] **`settings.py`:** `training_near_dupe_clip_threshold: float = 0.05` und `face_dedupe_similarity_threshold: float = 0.9` neu (Dataclass/Defaults/`_EXPECTED_TYPES`, floats als `(float, int)` wie `dupe_clip_threshold`); `dupe_threshold` final entfernt (Dataclass/Defaults/`_EXPECTED_TYPES` + `settings.example.json`).
- [x] **Tests:** `backend/tests/` gegreppt (`near_dupe`, `collection.*duplicates`, `edit_session`, `phash`) — nur `test_orientation_overwrite.py::test_overwrite_face_rotates_crop_and_refreshes_resolution_phash` betroffen, umbenannt + phash-Assertions entfernt; kein dedizierter Test für `/collections/{id}/duplicates` oder `compute_training_set_stats` vorhanden. `uv run pytest`: 189 grün, 13 vorbestehende Fails unberührt (identisch zu Phase 1). `uv run ruff check .`: nur vorbestehende, unberührte Fehler (alembic-Migrationen, `assets.py`, `comfyui_run_job.py`); alle Phase-2-Dateien einzeln grün.
- [x] **Doc-Update:** `docs/routes.md` — `/collections/{id}/duplicates`-Param-Semantik auf CLIP umgestellt.

## Report-Back

Umbau vollständig CLIP/Embedding-only; keine Abweichungen vom Plan. `settings.example.json`
zusätzlich bereinigt (dort stand `dupe_threshold` noch als Beispielwert, nicht im
Checklisten-Dateiscope, aber gleicher Kontrakt-Punkt).
