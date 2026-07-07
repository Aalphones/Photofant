# Phase 2 — Vektor-Dimension-Migration (768 → 1024)

**Komplexität:** heikel (Schema-Migration + Übergangs-Invariante) · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `backend/photofant/db/vector_index.py` — `EMBEDDING_DIM = 768`, `CREATE_TABLE_SQL` (`vec0(embedding float[768]
  distance_metric=cosine)`), `_serialize` (Dim-Gate), `load_vec_extension`. Die `vec0`-Tabelle heißt `vec_asset_embedding`.
- `backend/alembic/versions/0007_vector_index.py` — die Migration, die die `vec0`-Tabelle **erstellt** (Vorlage
  für Recreate; zeigt, wie `sqlite-vec` im Migrations-Kontext geladen wird — `load_vec_extension(op.get_bind())`).
- `backend/photofant/db/models.py` — `Asset.clip_embedding` (BLOB, deferred), `ProcessingLedger.embedding_done`.
- Konsumenten, die BLOBs direkt per `np.frombuffer` lesen und stapeln (dürfen keinen gemischten Dim-Zustand sehen):
  `jobs/dupe_scan_job.py` (`np.stack`), `api/duplicates.py`, `api/collections.py`, `collections/stats.py`,
  `api/review.py`, `api/search.py`.

## Warum die Übergangs-Invariante Pflicht ist
Sobald `EMBEDDING_DIM = 1024` gilt, wirft `_serialize` bei jedem alten 768-BLOB. Und `np.stack` im Dupe-Scan
crasht bei gemischten 768/1024-BLOBs. Deshalb muss die Migration **atomar** den Alt-Zustand ausräumen: Tabelle neu
(leer, 1024), alle `clip_embedding` auf `NULL`, alle `embedding_done` auf `False`. Danach ist der einzige gültige
Zustand „kein Embedding vorhanden" — die Konsumenten behandeln das bereits (409 `NO_EMBEDDING` in `search.py`,
`WHERE clip_embedding IS NOT NULL` überall). Der Re-Embed (Phase 3) füllt neu.

## AK der Phase
- [ ] `vector_index.EMBEDDING_DIM = 1024`; `CREATE_TABLE_SQL` entsprechend (`float[1024]`).
- [ ] Alembic-Migration (`XXXX_siglip2_dim_1024.py`):
      1. `DROP TABLE IF EXISTS vec_asset_embedding` + neu anlegen mit `float[1024]` (sqlite-vec laden wie in 0007).
      2. `UPDATE asset SET clip_embedding = NULL`.
      3. `UPDATE processing_ledger SET embedding_done = 0`.
      Downgrade: analog zurück auf 768 + gleiche NULL/Reset (Alt-Embeddings sind ohnehin verloren — dokumentieren).
- [ ] Nach der Migration liefert `POST /api/search/semantic` mit `like_asset_id` sauber 409 `NO_EMBEDDING`
      (statt Crash), solange nicht neu embedded wurde.
- [ ] `ruff check .` grün; `alembic upgrade head` + `downgrade -1` + `upgrade head` laufen fehlerfrei durch.

## Doc-Updates
- [ ] `docs/models.md` — Vermerk an `vec_asset_embedding` / `asset.clip_embedding`: Dimension 1024 (SigLIP2).

## Report-Back
