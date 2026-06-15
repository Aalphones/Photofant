# P1 · Phase 1 — Backend-Skeleton

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (API-Prefix, SSE-Schema)
- [Konzept](../../Konzept-Photofant.md) §2 (Architektur), §6.1 (Queue-Anforderung), §17 (Install & Start)
- [docs/conventions/python.md](../../conventions/python.md)

## Akzeptanzkriterien

- `uv run uvicorn photofant.main:app` startet; `GET /api/health` antwortet.
- In-Process-Job-Queue nimmt Jobs an, führt sie async aus, streamt Status über `GET /api/jobs/stream` (SSE).
- Alembic eingerichtet; Migration 0001 legt `app_config` an; DB-Datei entsteht unter konfigurierbarem Pfad (Default `./.photofant/db.sqlite`).

## Checkliste

- [ ] `backend/` als uv-Projekt: `pyproject.toml` (Python gepinnt, fastapi, uvicorn, sqlalchemy, alembic, sse-starlette o.ä.), Lockfile
- [ ] Package-Struktur `photofant/`: `main.py` (App-Factory), `api/` (Router), `db/` (Engine, Session), `jobs/` (Queue)
- [ ] Job-Queue: asyncio-basiert, in-process; Job = (id, kind, label, coro), Status-Übergänge queued→running→done/error; Subscriber-Mechanik für SSE
- [ ] `GET /api/jobs/stream` + `POST /api/jobs/demo` (Wegwerf-Job mit Schritt-Fortschritt)
- [ ] Alembic-Init + Migration `app_config (key TEXT PK, value TEXT)`
- [ ] `ruff` + `mypy`-Konfiguration in `pyproject.toml` gemäß linting.md
- [ ] Doc-Update: AGENTS.md Stack-Tabelle um gepinnte Versionen ergänzen

## Report-Back
