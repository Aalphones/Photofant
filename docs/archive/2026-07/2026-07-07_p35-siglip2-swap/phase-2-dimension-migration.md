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
- [x] `vector_index.EMBEDDING_DIM = 1024`; `CREATE_TABLE_SQL` entsprechend (`float[1024]`, aus der Konstante gebaut).
- [x] Alembic-Migration (`0032_siglip2_dim_1024.py`):
      1. `DROP TABLE IF EXISTS vec_asset_embedding` + neu anlegen mit `float[1024]` (sqlite-vec via `load_vec_extension` wie in 0007).
      2. `UPDATE asset SET clip_embedding = NULL`.
      3. `UPDATE processing_ledger SET embedding_done = 0`.
      Downgrade: symmetrisch zurück auf `float[768]` + gleiche NULL/Reset, Verlust dokumentiert. Dim-Literale
      stehen als Konstanten in der Migration (immutable Snapshot, nicht importiert).
- [ ] **(User-Smoke, Laufzeit)** Nach der Migration liefert `POST /api/search/semantic` mit `like_asset_id` sauber
      409 `NO_EMBEDDING` (statt Crash), solange nicht neu embedded wurde. Durch Design gedeckt (`search.py` behandelt
      NULL bereits), Bestätigung erst mit laufender Migration + Server.
- [x] `ruff check` auf den geänderten Dateien grün; Alembic parst die Migration, Kette korrekt (Kopf = 0032).
- [ ] **(User-Smoke, destruktiv)** `alembic upgrade head` + `downgrade -1` + `upgrade head` — nicht von mir gefahren:
      der Upgrade löscht alle Embeddings (Übergangs-Invariante), gehört an den Re-Embed in Phase 3. User führt aus.

## Doc-Updates
- [x] `docs/models.md` — `vec_asset_embedding.embedding` `float[1024]`, `asset.clip_embedding` 1024-dim (SigLIP2) vermerkt.

## Report-Back
- **Geändert:** `EMBEDDING_DIM 768 → 1024` (+ model-agnostischer Kommentar) in `db/vector_index.py`;
  neue Migration `0032_siglip2_dim_1024.py` (Recreate `vec0` bei 1024, alle `clip_embedding` NULL, alle
  `embedding_done` 0 — Übergangs-Invariante in beide Richtungen); `docs/models.md` nachgezogen.
- **Guard:** `warn_on_embedding_dim_mismatch` liest `EMBEDDING_DIM` live — keine Änderung nötig; warnt
  erwartungsgemäß bis SigLIP2 aktiv ist (FINDINGS Phase-2 abgehakt).
- **Offen (User):** `alembic upgrade head` fahren (löscht alle Embeddings — bewusst) und die 409-Prüfung;
  Re-Embed füllt in Phase 3 neu.
- **Nicht angefasst:** Gesichts-Index `vec_face_embedding` (512-dim, eigener Vektorraum) — außerhalb des Scope.
