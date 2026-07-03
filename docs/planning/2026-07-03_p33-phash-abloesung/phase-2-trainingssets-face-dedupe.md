# Phase 2 — Trainingssets + Face-Dedupe Backend

**Komplexität:** standard · **Status:** pending

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

- [ ] **`api/collections.py` `/duplicates`:** Query lädt `Asset.clip_embedding` statt `Asset.phash` (Filter `clip_embedding.is_not(None)`); Pairwise via numpy-Matmul (Muster `_compare_chunk_clip`: `np.frombuffer(float32)`, Stack, `chunk @ vectors.T`, Distanz = 1 − Similarity); `CollectionDupePairDto.phash_distance` → `clip_distance: float`; `similarity_pct = round((1 - clip_distance) * 100)`; `threshold`-Param + `_DUPE_MAX_THRESHOLD` auf CLIP-Distanz-Semantik (float, Kappung bei 0.5); Default aus `training_near_dupe_clip_threshold`; Sortierung nach `clip_distance` aufsteigend; `hamming_distance`-Import raus.
- [ ] **`collections/stats.py`:** `_near_dupe_rate(phashes)` → `_near_dupe_rate(embeddings)` auf CLIP-Basis: Blobs zu float32-Matrix, `matrix @ matrix.T`, Partner = Distanz ≤ `training_near_dupe_clip_threshold`; Query in `compute_training_set_stats` lädt `Asset.clip_embedding` statt `Asset.phash`; `_NEAR_DUPE_THRESHOLD`-Konstante + `hamming_distance`-Import raus. Struktur der `has_partner`-Logik beibehalten (Anteil Bilder mit ≥1 Partner).
- [ ] **`api/edit_sessions.py` — Face-Dedupe auf Embeddings:** `existing_phashes` → `existing_embeddings` (Query lädt `Face.embedding` statt `Face.phash`, `np.frombuffer(float32)`); im Detect-Loop den pHash-Berechnungsblock (imagehash) entfernen und stattdessen `face_dict["embedding"]` gegen `existing_embeddings` per Cosine vergleichen (Embeddings sind L2-normalisiert ⇒ Dot-Product); `similarity >= settings["face_dedupe_similarity_threshold"]` ⇒ Crop löschen + skip (Log-Zeile sinngemäß von „pHash-Dedupe" auf „Face-Dedupe" umbenennen — auch die übrigen Log-Präfixe im Block); `_phash_hamming` + `_PHASH_QUASI_IDENTICAL_THRESHOLD` raus; beim Anlegen der neuen Face-Row das `phash=`-Feld weglassen.
- [ ] **Face-/Asset-pHash-Schreiber entfernen:** `face_job.py` (`_compute_crop_phash` + Aufruf + `phash=`-Arg), `face_folder_scan_job.py` (pHash-Block + `phash=`-Arg), `api/faces.py` (pHash-Block + `phash=`-Arg), `orientation_overwrite.py` (beide Recompute-Zeilen + Importe von `compute_phash`/`compute_phash_hex`).
- [ ] **`clustering_job.py`:** `phash_distance=0` aus dem `ReviewItem(type="face_suggestion", …)`-Konstruktor (Spalte ist nullable).
- [ ] **`settings.py`:** `training_near_dupe_clip_threshold: float = 0.05` und `face_dedupe_similarity_threshold: float = 0.9` (Dataclass/Defaults/`_EXPECTED_TYPES`, floats als `(float, int)` wie `dupe_clip_threshold`).
- [ ] **Tests:** `backend/tests/` nach Nutzern der geänderten Symbole greppen (`near_dupe`, `collection.*duplicates`, `edit_session`), anpassen; `uv run pytest` betroffene Module + `uv run ruff check .`.
- [ ] **Doc-Update:** `docs/routes.md` — `/collections/{id}/duplicates`-Param-Semantik.

## Report-Back
