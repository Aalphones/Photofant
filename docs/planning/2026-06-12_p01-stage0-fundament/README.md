# P1 — Stage-0-Fundament

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §18 Stage 0 · Abhängigkeiten: keine

Walking Skeleton: Backend und Frontend stehen, sind verbunden, und ein Demo-Job läuft sichtbar über die Queue. Danach ist jede weitere Lieferung reine Feature-Arbeit.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Backend-Skeleton](phase-1-backend-skeleton.md) | standard | complete |
| 2 | [Frontend-Skeleton](phase-2-frontend-skeleton.md) | standard | complete |
| 3 | [Skripte & CI](phase-3-skripte-und-ci.md) | mechanisch | pending |

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

## Files touched

## Commits

## Deviations from plan

## Follow-ups
