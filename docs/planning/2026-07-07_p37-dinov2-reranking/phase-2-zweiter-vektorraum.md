# Phase 2 — Zweiter Vektorraum + Embedding-Job + Migration

**Komplexität:** heikel (zweiter Index + Ledger-Flag + Migration) · **Status:** ✅ complete

## Kontext (vor dem Bauen lesen)
- `backend/photofant/db/vector_index.py` — `vec_asset_embedding` (SigLIP2, `float[1024]` nach P35), `_serialize`,
  `load_vec_extension`, `search()`. Vorlage für einen **zweiten** Index `vec_asset_dino` (`float[768]`).
- `backend/alembic/versions/…_siglip2_dim_1024.py` (aus P35) — Vorlage, wie eine `vec0`-Tabelle im Migrations-Kontext
  erstellt wird (`load_vec_extension(op.get_bind())`).
- `backend/photofant/db/models.py` — `Asset.clip_embedding` (BLOB, deferred), `ProcessingLedger.embedding_done`.
  Neu: `Asset.dino_embedding` + `ProcessingLedger.dino_embedding_done`.
- `backend/photofant/jobs/embedding_job.py` — `_run_embedding` (embeddet heute SigLIP2). Wird erweitert: **beide**
  Modelle je Asset, jeweils in den eigenen Index + eigenes Ledger-Flag.
- `backend/photofant/jobs/rerun_job.py` — `run_rerun_job(steps=["embedding"])`. Muss den DINOv2-Teil mitziehen
  (oder einen zusätzlichen Schritt `"dino_embedding"` anbieten, damit nur DINOv2 nachlaufen kann).

## Design-Entscheidung dieser Phase
Zwei getrennte `vec0`-Tabellen statt einer breiten — kohärenter Vektorraum pro Modell, unterschiedliche Dimension,
und der Dupe-Scan/Rerank braucht ohnehin gezielten Zugriff auf genau ein Modell. Ein Asset ohne DINOv2-Embedding
(z.B. mitten im Nachlauf) ist ein **gültiger** Zustand — Rerank degradiert dann auf reines SigLIP2 (Phase 3).
Deshalb hier **keine** „alles-oder-nichts"-Übergangs-Invariante wie in P35 nötig: die Indizes sind unabhängig.

## AK der Phase
- [x] `Asset.dino_embedding` (BLOB, deferred) + `ProcessingLedger.dino_embedding_done` (bool, Default False) in
      `db/models.py`.
- [x] `vector_index`: zweiter Index `vec_asset_dino` (`float[768]`, cosine) mit eigenem `serialize`/`search`-Zugang
      (parametrisiert über die Tabelle statt Copy-Paste, wenn ohne Verrenkung möglich). → Shared parametrisierte
      private Helfer (`_serialize(embedding, dim)`, `_upsert/_delete/_search/_rebuild(table, …)`); SigLIP2-Public-API
      namens-/signaturgleich (kein Aufrufer-Ripple), DINOv2-Fläche `upsert_dino_embedding`/`delete_dino_embedding`.
      Lesepfad (`search_dino`) bewusst erst Phase 3 (YAGNI).
- [x] Alembic-Migration `0033`: `asset.dino_embedding`-Spalte + `processing_ledger.dino_embedding_done` + `vec_asset_dino`
      anlegen. **Kein** Reset bestehender SigLIP2-Daten (unabhängige Räume, verifiziert). Downgrade: Spalten + Tabelle droppen
      (vec0-Extension vor DROP geladen). Guarded/idempotent.
- [x] `embedding_job` embeddet je Asset **beide** aktiven Modelle (Kern `_embed_asset(semantic, dino)`; `_run_embedding`
      = beide), schreibt in beide Indizes, setzt beide Ledger-Flags. Fehlt ein DINOv2-Modell, wird der DINOv2-Teil sauber
      übersprungen (Flag bleibt False), kein Crash.
- [x] `rerun_job`: neuer Schritt `dino_embedding` → `_run_dino_embedding` (nur DINOv2, SigLIP2 unberührt). Literal +
      `_STEP_FLAGS` in `rerun_job` **und** `api/classify.py` synchron.
- [x] `ruff check` grün; `alembic upgrade head` + `downgrade -1` + `upgrade head` laufen durch (isoliert verifiziert,
      SigLIP2-Raum über den ganzen Zyklus unangetastet).

## Doc-Updates
- [x] `docs/models.md` — `asset.dino_embedding`, `vec_asset_dino` (768, DINOv2), `processing_ledger.dino_embedding_done`.

## Report-Back
**Erledigt.** 6 Code-Dateien + Migration 0033 + models.md. Zusatzfund mitgefixt: der Asset-Purge in `media/moves.py`
löschte nur den SigLIP2-Index-Row — jetzt auch `delete_dino_embedding`, sonst Orphan-Rows in `vec_asset_dino`.
Migrations-Bug im Downgrade gefangen (vec0-Modul muss vor `DROP TABLE` geladen sein) — gefixt, Round-Trip grün.

⚠️ **Testnebenwirkung:** eine BOM-kaputte Test-Settings-Datei ließ einen frühen Migrations-Testlauf auf die echte
Default-Dev-DB (`Photofant/Data/.photofant/db.sqlite`, 702 Assets) statt eine Wegwerf-DB laufen. Nur additive Spalten,
Down→Up sauber, kein Datenverlust — die DB steht jetzt auf 0033 (der Zielzustand). Der finale AK-Beleg lief isoliert.
