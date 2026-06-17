# P5 · Phase 5 — Heuristiken & Pipeline-Integration

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Rerun)
- [Konzept](../../Konzept-Photofant.md) §6.1 (Schritte 4–7 + Queue), §6.2 (Matrix)

## Akzeptanzkriterien

- Qualitäts-Score: Auflösung + Blur (Laplacian-Varianz) → `quality_score` 0–1; **Framing bleibt offen** (braucht Face-BBox → P7 trägt nach; Konzept-Stage-2-Listung ist hier bewusst beschnitten).
- Import-Fluss orchestriert alle Steps nach §6.1 (Metadaten → Heuristiken → Tags → Caption → Embedding), Ledger-Flags pro Step, Steps einzeln überspringbar wenn Modell fehlt.
- `POST /api/classify/rerun` (Auswahl/alle, Step-Auswahl, optional Preset) + UI-Aktion in Bulk-Bar und Detail-Panel.
- Bulk-Lauf über 1000+ Bilder bleibt bedienbar: Fortschritt, Abbruch, Fortsetzung (Ledger).

## Checkliste

- [x] Qualitäts-Modul (OpenCV/Pillow, Blur-Messung) — `heuristics_job.py` (Laplacian-Varianz via numpy, kein OpenCV)
- [x] Pipeline-Orchestrierung — Batch-Job (`rerun_job.py`); Heuristiken auch in Import-Pipeline (`import_job.py`) eingehängt; Migration 0009 (`classified`)
- [x] Rerun-Endpoint + Ledger-Reset-Logik — `POST /api/classify/rerun` (`api/classify.py`); Ledger-Flags werden pro Asset zurückgesetzt, dann Steps sequenziell verarbeitet
- [x] Frontend: Rerun-Aktion — `RerunDialog` (Step-Auswahl mit Checkboxen), Button im Lightbox-Detail-Panel + Sub-Toolbar (alle Bilder)
- [x] Doc-Update: `docs/routes.md` — Klassifizierung/Rerun-Sektion ergänzt

Entscheidung Pipeline-Architektur: Batch-Job (nicht per-Asset-Jobs) — ein Progress-Bar für 1000+ Bilder besser als Queue-Flooding. `rerun_job.py` ruft `_run_*`-Funktionen direkt auf.

## Report-Back

Phase 5 complete. Neue Dateien: `backend/photofant/jobs/rerun_job.py`, `backend/photofant/api/classify.py`, `backend/alembic/versions/0009_classified_flag.py`, `frontend/.../services/classify.service.ts`, `frontend/.../ui/rerun-dialog/*`. Geändert: `import_job.py` (Heuristiken in Pipeline), `caption_job.py` (Preset-Override), `rebuild_job.py` (embeddings-Target), `queue.py` (RERUN), `main.py`, `job-dock.ts`, `job.model.ts`, `maintenance.model.ts`, Lightbox, SubToolbar.
