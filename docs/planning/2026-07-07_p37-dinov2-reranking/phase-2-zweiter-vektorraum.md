# Phase 2 — Zweiter Vektorraum + Embedding-Job + Migration

**Komplexität:** heikel (zweiter Index + Ledger-Flag + Migration) · **Status:** pending

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
- [ ] `Asset.dino_embedding` (BLOB, deferred) + `ProcessingLedger.dino_embedding_done` (bool, Default False) in
      `db/models.py`.
- [ ] `vector_index`: zweiter Index `vec_asset_dino` (`float[768]`, cosine) mit eigenem `serialize`/`search`-Zugang
      (parametrisiert über die Tabelle statt Copy-Paste, wenn ohne Verrenkung möglich).
- [ ] Alembic-Migration: `asset.dino_embedding`-Spalte + `processing_ledger.dino_embedding_done` + `vec_asset_dino`
      anlegen. **Kein** Reset bestehender SigLIP2-Daten (unabhängige Räume). Downgrade: Spalten + Tabelle droppen.
- [ ] `embedding_job._run_embedding` embeddet je Asset **beide** aktiven Modelle (SigLIP2 über `role=semantic_search`,
      DINOv2 über `role=visual_rerank`), schreibt in beide Indizes, setzt beide Ledger-Flags. Fehlt ein DINOv2-Modell
      (nicht aktiviert), wird der DINOv2-Teil sauber übersprungen (Flag bleibt False), kein Crash.
- [ ] `rerun_job` kann „nur DINOv2 nachrechnen" (Schritt `dino_embedding` oder Einschluss im `embedding`-Schritt) —
      damit eine bestehende Bibliothek DINOv2 nachträglich bekommt, ohne SigLIP2 neu zu rechnen.
- [ ] `ruff check .` grün; `alembic upgrade head` + `downgrade -1` + `upgrade head` laufen durch.

## Doc-Updates
- [ ] `docs/models.md` — `asset.dino_embedding`, `vec_asset_dino` (768, DINOv2), `processing_ledger.dino_embedding_done`.

## Report-Back
