# P1 · Phase 1 — Backend-Skeleton

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (API-Prefix, SSE-Schema)
- [Konzept](../../Konzept-Photofant.md) §2 (Architektur), §6.1 (Queue-Anforderung), §17 (Install & Start)
- [docs/conventions/python.md](../../conventions/python.md)

## Akzeptanzkriterien

- `uv run uvicorn photofant.main:app` startet; `GET /api/health` antwortet.
- In-Process-Job-Queue nimmt Jobs an, führt sie async aus, streamt Status über `GET /api/jobs/stream` (SSE).
- Alembic eingerichtet; Migration 0001 legt `app_config` an; DB-Datei entsteht unter konfigurierbarem Pfad (Default `./.photofant/db.sqlite`).

## Checkliste

- [x] `backend/` als uv-Projekt: `pyproject.toml` (Python gepinnt, fastapi, uvicorn, sqlalchemy, alembic, sse-starlette o.ä.), Lockfile
- [x] Package-Struktur `photofant/`: `main.py` (App-Factory), `api/` (Router), `db/` (Engine, Session), `jobs/` (Queue)
- [x] Job-Queue: asyncio-basiert, in-process; Job = (id, kind, label, coro), Status-Übergänge queued→running→done/error; Subscriber-Mechanik für SSE
- [x] `GET /api/jobs/stream` + `POST /api/jobs/demo` (Wegwerf-Job mit Schritt-Fortschritt)
- [x] Alembic-Init + Migration `app_config (key TEXT PK, value TEXT)`
- [x] `ruff` + `mypy`-Konfiguration in `pyproject.toml` gemäß linting.md
- [x] Doc-Update: AGENTS.md Stack-Tabelle um gepinnte Versionen ergänzen

## Report-Back

- `GET /api/health` → `{"status":"ok","version":"0.1.0"}` ✓
- Job-Queue asyncio, Subscriber-Mechanik, SSE-Stream mit Ping-Heartbeat (15 s) ✓
- `POST /api/jobs/demo` startet Wegwerf-Job mit 5 × 1 s Schritten über CoroFactory-Pattern ✓
- Alembic 0001 läuft durch; `app_config`-Tabelle in `.photofant/db.sqlite` ✓
- ruff + mypy --strict grün auf allen 10 Source-Files ✓
- uv 0.11.21, Python 3.12, FastAPI 0.115, Uvicorn 0.49, SQLAlchemy 2.x, Alembic 1.14 ✓

**Deviation:** uv war nicht installiert → Standalone-Installer astral.sh ausgeführt (wie Convention vorschreibt).
**Note:** `VIRTUAL_ENV=C:\Python312` Warning beim `uv run` ist harmlos — system-venv kollidiert nicht, wird ignoriert.
