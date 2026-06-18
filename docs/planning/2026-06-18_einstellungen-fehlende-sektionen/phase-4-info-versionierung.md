# Einstellungen fehlende Sektionen · Phase 4 — Info + Versionierung

> Rating: **standard** · Status: pending

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

- [ ] **`api/health.py`**: `VERSION = "0.1.0"` ersetzen durch:
  ```python
  from importlib.metadata import version, PackageNotFoundError
  try:
      _APP_VERSION = version("photofant-backend")
  except PackageNotFoundError:
      _APP_VERSION = "dev"   # Fallback beim Direktstart ohne `uv run`/install
  ```
  `HealthResponse.version` auf `_APP_VERSION` setzen.
- [ ] **Neuer Endpoint `GET /api/info`** (neues File `api/info.py` oder Erweiterung von `health.py`):
  - `version` — aus `importlib.metadata`
  - `python_version` — `sys.version`
  - `db_path`, `db_size_bytes` — Pfad aus `get_data_root_base()`, `Path.stat().st_size`
  - `cache_db_path`, `cache_db_size_bytes` — analog für `thumbnails.sqlite`
  - `onnx_version` — `onnxruntime.__version__`
  - `last_migration` — letzte Alembic-Revision aus `alembic_version`-Tabelle
  - `gpu_name`, `vram_gb`, `cuda_version` — optional über `onnxruntime.get_device()` bzw. CUDA-Check; `null` wenn nicht vorhanden (GPU nicht Pflicht)
  - `env_flags` — prüft `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` aus `os.environ`
- [ ] **`api/__init__.py`** (Router-Mount): neuen `/api/info`-Router registrieren
- [ ] Doc-Update: `docs/routes.md` — neuen Endpoint dokumentieren

### Konventions-Regel

- [ ] **`docs/conventions/python.md`** — neue Sektion "Versionierung":
  - Einzige Pflege-Stelle: `pyproject.toml` `[project] version`
  - Lesen via `importlib.metadata.version("photofant-backend")`
  - `PackageNotFoundError`-Fallback `"dev"` für direkten `python -m`-Start
  - Keine `VERSION = "..."` Konstante in beliebiger Python-Datei

### Frontend

- [ ] **Neues NgRx-Action/Effect-Paar** (oder `maintenance`-Slice nutzen): `loadAppInfo()` → `GET /api/info` → `loadAppInfoSuccess({ info })`
- [ ] **Neues Model-Interface `AppInfo`** in `models/`
- [ ] **`einstellungen.ts`**: Sektion "Info" mit KV-Grid analog zum Prototyp (`SectionInfo` in `settings.jsx`); Versionsnummer, DB-Pfad/-Größe, ONNX-Version, letzte Migration, GPU-Details, Env-Flags; Hinweis-Note "Kein Netzwerkverkehr"
- [ ] Dispatch `loadAppInfo()` beim Öffnen der Info-Sektion (lazy, nicht beim App-Start)

## Report-Back
