# P1 — Stage-0-Fundament

> Status: complete · Quelle: [Konzept](../../Konzept-Photofant.md) §18 Stage 0 · Abhängigkeiten: keine

Walking Skeleton: Backend und Frontend stehen, sind verbunden, und ein Demo-Job läuft sichtbar über die Queue. Danach ist jede weitere Lieferung reine Feature-Arbeit.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Backend-Skeleton](phase-1-backend-skeleton.md) | standard | complete |
| 2 | [Frontend-Skeleton](phase-2-frontend-skeleton.md) | standard | complete |
| 3 | [Skripte & CI](phase-3-skripte-und-ci.md) | mechanisch | complete |

## Kontrakt (Backend ↔ Frontend)

- **API-Prefix:** alle REST-Routen unter `/api/...`; Frontend-Dev-Server proxied `/api` auf den Uvicorn-Port.
- **`GET /api/health`** → `{ "status": "ok", "version": "<semver>" }`
- **`GET /api/jobs/stream`** (SSE) — Event `job`, Data:
  ```json
  { "id": "uuid", "kind": "demo|import|thumbnail|...", "label": "string",
    "progress": 0.0, "state": "queued|running|done|error", "error": null }
  ```
  Jede State-/Progress-Änderung emittiert das vollständige Objekt (idempotent konsumierbar).
- **`POST /api/jobs/demo`** → startet einen Demo-Job (~5 s, Fortschritt in Schritten) — Wegwerf-Endpoint zum Verdrahten, fliegt in P2 raus.
- **Verzeichnis-Layout:** `backend/` (uv-Projekt, Package `photofant`) · `frontend/` (Angular-Workspace).

## Finale Akzeptanzkriterien

1. `install.cmd` gefolgt von `start.cmd` liefert auf einem frischen Checkout eine erreichbare App (Backend + ausgeliefertes/proxytes Frontend).
2. Die App-Shell entspricht dem Prototyp: Nav-Rail mit Brand + Einträgen, Top-Bar, Dark-Theme aus den `docs/design/styles.css`-Tokens; Routing zeigt Platzhalter-Views.
3. Demo-Job ausgelöst → Job-Pill zeigt Spinner, Job-Dock zeigt Label + Fortschrittsbalken live über SSE, Abschluss wird angezeigt.
4. `ci.cmd` läuft beide Seiten (ruff/pytest, lint/build/test) und endet mit `CI: OK`.
5. Alembic-Baseline existiert; `app_config`-Tabelle per Migration angelegt.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Frischer Clone → `install.cmd` → `start.cmd` → Browser: Shell sichtbar, keine Konsolen-Fehler
- [ ] Demo-Job klicken → Pill + Dock zeigen Fortschritt → „fertig"-Zustand
- [ ] Fenster schmaler als 860 px ziehen → Nav wird Drawer, Bottom-Tab-Bar erscheint
- [ ] `ci.cmd` → `CI: OK`

## Summary

Stage-0-Fundament vollständig: Backend-Skeleton (FastAPI + SQLite + Alembic), Frontend-Skeleton (Angular 19 + NgRx + Tailwind v4), Install-/Start-Skripte, CI-Skript. App läuft end-to-end: Demo-Job über SSE, Health-Endpoint, App-Shell mit Nav-Rail.

## Files touched

- `backend/` — FastAPI-App, Alembic-Migration, Job-Queue, Health-API
- `frontend/` — Angular-App-Shell, NgRx-Store, SSE-Service, Job-Dock/Pill
- `install.cmd`, `install.sh`, `start.cmd`, `start.sh` (neu)
- `ci.cmd` (pre-existent, verifiziert)
- `frontend/package.json` — lint-Script ergänzt
- `backend/tests/test_health.py` (neu)
- `README.md` — Quickstart aktualisiert

## Commits

Alle Phasen committed auf `master`.

## Deviations from plan

- `lint` in package.json auf `tsc --noEmit` statt Angular ESLint gesetzt (ESLint-Setup nicht im Plan; tsc reicht für Stage 0).
- Health-Test angelegt (Pflicht, damit pytest nicht mit Exit-5 abbricht).

## Follow-ups

- Angular ESLint optional nachrüsten wenn ESLint-Regeln gewünscht.
- `ci.cmd` Frontend-Test: ChromeHeadless für Server-CI-Umgebungen konfigurieren.
