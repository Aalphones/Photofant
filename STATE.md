# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p22-knowledge-engine/` — **alle 4 Phasen complete**
**Phase:** 4/4 — Rebuild-Job + Vault↔Cache-Reconcile (✅ complete)
**Nächster Schritt:** Smoke-Checkliste durch den User (siehe unten), dann P22 archivieren
(`git mv docs/planning/2026-07-01_p22-knowledge-engine → docs/archive/2026-07/`) und STATE auf den
nächsten Backlog-Plan zeigen lassen (Kandidaten: P23 Wizard, P24 Integration, P25 Lore, P26 Empfehlungen,
P27 Gemma, P34 MCP).

**Smoke-Checkliste (User prüft, P22 gesamt):**
1. `curl POST /api/knowledge/entities` mit Beispiel-Entity → Datei liegt unter `knowledge/actors/…md`.
2. `curl GET .../search?q=RDJ` findet sie über den Alias.
3. Wartung → „Wissens-Schnellsuche neu aufbauen" → Suche findet die Entity wieder (Rebuild aus Vault).
   Ebenso „Notiz-Änderungen übernehmen" (Reconcile) nach einem Hand-Edit einer .md.
4. `PATCH` mit `owner=inferred` auf ein user-Feld → wird abgelehnt (409/403).

**Phase 4 abgeschlossen (2026-07-08):** Rebuild + Vault↔Cache-Reconcile. `knowledge/maintenance.py`
(`rebuild_cache` = `clear_all()` + Reimport; `reconcile_cache` = Reimport, Markdown gewinnt, +
Entfernung von Cache-Zeilen ohne Vault-*Datei* — Existenzprüfung, nicht Import-Erfolg, damit ein
Frontmatter-Tippfehler keinen Datenverlust auslöst). `vault.py` +`iter_entity_files`/`load_all`,
`repository.py` +`clear_all`/`all`. **Entscheidung (Plan überließ sie mir):** an bestehenden Rebuild
gehängt statt eigener `jobs/knowledge_*_job.py` — `RebuildTarget` +`knowledge`/`knowledge_reconcile`,
Frontend nutzt den `triggerRebuild`-Strang (null neue NgRx), Wartungs-Karte „Wissensbasis" mit 2 Buttons.
🟡 Reconcile ohne mtime (voller Re-Import; kein Zeitstempel im Cache). 6 neue pytest-Tests grün,
ruff/mypy auf angefassten Dateien grün, tsc grün. Docs (code-map, routes, README, FINDINGS) nachgezogen.

**Phase 3 abgeschlossen (2026-07-08):** KnowledgeService + REST-API. `knowledge/service.py`
(`KnowledgeService` — einzige Mutationsschicht, Markdown-first: erst Vault, dann Cache-Upsert;
Ownership entity-weit statt pro Feld, `owner=user` erzwingt `confidence=1.0`; `find_entity` löst
mehrdeutige Alias-Treffer **nicht** still auf, sondern wirft `AmbiguousEntityError`). `Vault.delete_entity`
ergänzt (reines I/O, wie `save_entity`). `api/knowledge.py` — REST-CRUD + Beziehungen + Lore-Stub,
Registrierung in `main.py`. `owner` ist ein optionales Request-Feld (Default `"user"`) auf allen
Schreibrouten, damit die Ownership-Ablehnung per REST testbar ist (Plan-Smoke-Checkliste #4).
Routing-Falle gefunden + gefixt: `{entity_id:path}` matcht Slashes, Suffix-Routen (`/relationships`,
`/lore`) müssen vor der bloßen `/entities/{id}`-Route stehen, sonst verschluckt deren Pattern jede
tiefere Anfrage gleicher HTTP-Methode. 32 neue pytest-Tests (20 Service, 12 REST), alle grün. mypy
projektweit weiterhin exakt 124 vorbestehende Fehler (0 neue), ruff auf allen angefassten Dateien
grün. Docs (`routes.md`, `code-map.md`, README-Phasentabelle, FINDINGS) nachgezogen.

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
