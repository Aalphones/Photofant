# P1 · Phase 3 — Skripte & CI

> Rating: mechanisch · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — finale AK
- [Konzept](../../Konzept-Photofant.md) §17 (Install & Start)
- `ci.cmd` (Root — existiert, prüft Backend/Frontend sobald vorhanden)

## Akzeptanzkriterien

- `install.cmd` + `install.sh`: venv via uv, gepinnte Dependencies, `npm ci` im Frontend — idempotent wiederholbar.
- `start.cmd` + `start.sh`: Backend (Uvicorn) + Frontend (Dev-Server oder statisch ausgeliefertes Build) mit einem Aufruf.
- `ci.cmd` läuft auf dem realen Skeleton grün durch.
- README-Quickstart ersetzt den „noch kein Code"-Platzhalter durch echte Befehle.

## Checkliste

- [x] `install.cmd` / `install.sh` (uv sync, npm ci)
- [x] `start.cmd` / `start.sh` (Backend + Frontend, sinnvolle Ports, Hinweis-Ausgabe)
- [x] `ci.cmd` gegen das Skeleton verifizieren, ggf. Befehle nachziehen
- [x] Doc-Update: README.md Quickstart (Prerequisites: uv, Node; Install/Run/Test)
- [x] Doc-Update: AGENTS.md CI-Sektion prüfen (keine Änderung nötig)

## Report-Back

- `install.cmd` / `install.sh` angelegt — uv sync --dev + npm ci, idempotent.
- `start.cmd` / `start.sh` angelegt — Alembic upgrade head, dann Backend + Frontend parallel.
- `frontend/package.json`: `"lint": "tsc --noEmit -p tsconfig.app.json"` ergänzt (fehlte, ci.cmd würde sonst brechen).
- `backend/tests/test_health.py` angelegt — pytest-exit-code-5 (keine Tests) würde CI-FAILED auslösen.
- `README.md` Quickstart aktualisiert.
- Ruff ✅ · pytest 1/1 ✅ · tsc --noEmit ✅ · ng build ✅
