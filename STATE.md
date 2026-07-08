# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p22-knowledge-engine/`
**Phase:** 3/4 — KnowledgeService + REST-API (standard, noch nicht begonnen)
**Nächster Schritt:** Phase 3 von P22 — `knowledge/service.py` (`KnowledgeService`, orchestriert
`vault` + `repository` + `validator`, setzt die Ownership-Regel durch) + `api/knowledge.py` +
Registrierung in `main.py`. Kontext in `phase-3-service-api.md` + README-Kontrakt. Zwei Findings
aus Phase 2 vorab lesen: `vault.save_entity`/`EntityRepository.upsert_from_vault` sind reines I/O
(keine Ownership-Prüfung dort — die macht der Service vor jedem Schreiben), und
`find_by_alias`/`search` liefern Listen ohne Mehrdeutigkeits-Auflösung (Service muss entscheiden,
was bei mehreren Alias-Treffern passiert).

**Phase 2 abgeschlossen (2026-07-08):** SQLite-Cache + Repositories. Migration `0034_knowledge_cache.py`
(`knowledge_entities`/`_relationships`/`_sources`/`_media_links`, kein `ON DELETE CASCADE` — SQLite-FK-
Enforcement ist projektweit aus, Löschen läuft explizit in Python). `knowledge/repository.py`
(`EntityRepository`, `RelationshipRepository`). 7 pytest-Tests (Testpflicht aus
`docs/conventions/testing.md` sticht hier das private-Profil-Standardverhalten „keine Tests").
Migration up/down/up manuell gegen Wegwerf-SQLite verifiziert. mypy/ruff auf den angefassten
Dateien grün (0 neue Fehler; Projekt-Baseline hat 124 vorbestehende, unabhängige mypy-Fehler).
Docs (`models.md`, `code-map.md`) nachgezogen.

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
- 124 vorbestehende `mypy --strict`-Fehler quer über die Codebase (u.a. `api/assets.py`,
  `api/comfyui.py`, `jobs/*`) — unabhängig von P22, nicht angefasst. Kein Vollprojekt-Grün-Gate
  aktiv; neue P22-Dateien sind sauber.
