# P1 · Phase 3 — Skripte & CI

> Rating: mechanisch · Status: pending

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

- [ ] `install.cmd` / `install.sh` (uv sync, npm ci)
- [ ] `start.cmd` / `start.sh` (Backend + Frontend, sinnvolle Ports, Hinweis-Ausgabe)
- [ ] `ci.cmd` gegen das Skeleton verifizieren, ggf. Befehle nachziehen
- [ ] Doc-Update: README.md Quickstart (Prerequisites: uv, Node; Install/Run/Test)
- [ ] Doc-Update: AGENTS.md CI-Sektion prüfen

## Report-Back
