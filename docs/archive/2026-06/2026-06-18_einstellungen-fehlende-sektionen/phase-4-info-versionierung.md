# Einstellungen fehlende Sektionen · Phase 4 — Info + Versionierung

> Rating: **standard** · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, `/api/info`-Schema
- `backend/photofant/api/health.py` — `VERSION = "0.1.0"` hartkodiert (Problem: dupliziert `pyproject.toml`)
- `backend/pyproject.toml` — `version = "0.1.0"` (Single Source of Truth nach diesem Plan)
- Es gibt **keine** projektweite Versionierungs-Regel — diese Phase legt eine fest

## Versions-Problem (Status heute)

`health.py` definiert `VERSION = "0.1.0"` als eigene Konstante. `pyproject.toml` hat ebenfalls `version = "0.1.0"`. Zwei Stellen, die synchron gehalten werden müssen — Fehlerquelle.

**Lösung:** `importlib.metadata.version("photofant-backend")` liest zur Laufzeit aus dem installierten Paket, das seinen Wert aus `pyproject.toml` bekommt. Einzige Versionspflege-Stelle: `pyproject.toml`.

**Neue Projekt-Regel** (in `docs/conventions/` festhalten): Version wird ausschließlich in `pyproject.toml` gepflegt. Weder `health.py` noch irgendeine andere Python-Datei darf eine `VERSION`-Konstante definieren.

## Akzeptanzkriterien

- `GET /api/health` liefert `version` aus `importlib.metadata` statt Konstante.
- Neuer Endpoint `GET /api/info` liefert vollständige System-Details (s. README-Kontrakt).
- Versions-Anzeige im Info-Tab zeigt denselben Wert wie `pyproject.toml`.
- Neue Regel in `docs/conventions/python.md` dokumentiert.
- Kein `VERSION = "..."` mehr in Python-Code.

## Checkliste

### Backend

- [x] **`api/health.py`**: `VERSION = "0.1.0"` ersetzen durch:
  ```python
  from importlib.metadata import version, PackageNotFoundError
  try:
      _APP_VERSION = version("photofant-backend")
  except PackageNotFoundError:
      _APP_VERSION = "dev"   # Fallback beim Direktstart ohne `uv run`/install
  ```
  `HealthResponse.version` auf `_APP_VERSION` setzen.
- [x] **Neuer Endpoint `GET /api/info`** (`api/info.py`): version, python_version, db_path/size, cache_db_path/size, onnx_version, last_migration, gpu_name/vram_gb/cuda_version (via nvidia-smi, nullable), env_flags
- [x] **`main.py`**: `info.router` registriert
- [x] Doc-Update: `docs/routes.md` — neuen Endpoint dokumentiert

### Konventions-Regel

- [x] **`docs/conventions/python.md`** — neue Sektion "Versionierung" ergänzt

### Frontend

- [x] **`loadAppInfo` Actions/Effect** in `maintenance`-Slice (actions, reducer, effects, selectors)
- [x] **Neues Model-Interface `AppInfo`** in `models/app-info.model.ts` + `models/index.ts`
- [x] **`maintenance.service.ts`**: `loadAppInfo()` → `GET /api/info`
- [x] **`einstellungen.ts`**: Sektion "Info" mit KV-Grid; Dispatch `loadAppInfo()` beim Öffnen der Einstellungen

## Report-Back
