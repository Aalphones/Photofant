# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p22-knowledge-engine/`
**Phase:** 2/4 — SQLite-Cache + Repositories (standard, noch nicht begonnen)
**Nächster Schritt:** Phase 2 von P22 — Cache-Tabellen `knowledge_entities`/`knowledge_relationships`/
`knowledge_sources`/`knowledge_media_links` (Namespace `knowledge_*`, reiner Cache) + Alembic-Migration +
Repositories. Kontext in `phase-2-*.md` + README-Kontrakt. Die Owner-Priorität/Overwrite-Regel liegt
schon in `knowledge/schema.py` (nicht neu erfinden — FINDINGS-Eintrag für Phase 2).

**Phase 1 abgeschlossen (2026-07-08):** Vault + Entity-Schema + Parser. Paket `backend/photofant/knowledge/`
(`schema`, `parser`, `validator`, `domains`, `vault`) + `domains/movies.yaml`, settings-Block `knowledge`,
ADR-025, code-map-Zeile. Alle AK verifiziert, mypy/ruff grün. Zwei Kontrakt-Korrekturen (snake_case-Settings,
ADR-Nummer 025 statt 010) in README + FINDINGS festgehalten.

**Offene Follow-ups (🟡, nicht blockierend):**
- Text-Semantiksuche-Umschalter smoke-testen — Checkliste in
  `docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`.
- `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` ohne Aufrufer (aus P36).
- `POST /api/search/semantic`s `query`-Zweig ist totes Backend-Duplikat (aus P36).
- P37-Smoke-Checklisten #1 (Rerank-Qualität) + #2 (Dupe-Schwellwert-Kalibrierung) stehen aus —
  Nutzer-Aufgabe am realen Bild-Set, siehe archiviertes P37-README.
- Ohne aktives DINOv2-Modell läuft kein automatischer Duplikat-Check mehr beim Import (ADR-024).
- 13 vorbestehende Test-Failures in `test_comfyui_run.py`/`test_comfyui_auto_import.py`/
  `test_caption_config.py` (Signatur-Drift `run_comfyui_run_job` fehlt `job_version_inputs`) —
  unabhängig von P22, nicht angefasst.
