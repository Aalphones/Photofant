# Settings-JSON-Infrastruktur · Phase 1 — Schema + Infrastruktur

> Rating: **standard** · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Location-Entscheidung, Schema, Bootstrap-Reihenfolge
- `backend/photofant/config.py` — `get_data_root_base()`, `get_data_root()`, `get_models_dir()` — werden umgebaut
- `backend/photofant/api/config.py` — `_read_config()`, `patch_config()` — werden auf settings.json umgestellt

## Akzeptanzkriterien

- Neues Modul `backend/photofant/settings.py` stellt alle Settings-Operationen bereit.
- `GET /api/config` liest aus `settings.json`; `PATCH /api/config` schreibt atomar in `settings.json`.
- `config.py` liest `data_root` und `models_dir` aus `settings.py` statt aus Env + DB.
- `settings.example.json` liegt im Repo-Root; `settings.json` ist gitignored.
- Backend startet ohne Env-Vars.

## Checkliste

### Neues Modul `backend/photofant/settings.py`

- [ ] Dataclass/TypedDict `AppSettings` mit allen Keys aus dem Schema (typsicher, kein Any)
- [ ] `SETTINGS_DEFAULTS: AppSettings` — alle Defaults definiert
- [ ] `get_settings_path() -> Path`:
  - Prüft `PHOTOFANT_SETTINGS_PATH` env → absoluten Pfad zurückgeben
  - Sonst: `Path.cwd() / ".photofant" / "settings.json"` (Ordner wird angelegt falls nicht vorhanden)
- [ ] `load_settings() -> AppSettings`:
  - Liest `settings.json` wenn vorhanden; `json.JSONDecodeError` → Fallback zu Defaults + Warning-Log
  - Merged Defaults ← Datei (fehlende Keys aus Defaults ergänzen)
  - Gibt `AppSettings` zurück
- [ ] `save_settings(settings: AppSettings) -> None`:
  - Atomares Schreiben: in `.photofant/settings.json.tmp` schreiben, dann `rename()` (OS-atomar)
  - `indent=2`, `ensure_ascii=False`
- [ ] `patch_settings(partial: dict) -> AppSettings`:
  - `load_settings()` → merge partial → `save_settings()` → return neue Settings
  - Typvalidierung: bekannte Keys auf erwarteten Typ prüfen (TypeError → 422 nach oben reichen)
- [ ] `ensure_settings_file() -> None`: beim App-Start aufrufen — legt Datei mit Defaults an wenn nicht vorhanden

### `backend/photofant/config.py` umbauen

- [ ] `get_data_root_base()`: liest `data_root` aus `load_settings()` statt Env; `null` → Default `Path("Data")`
- [ ] `get_data_root()`: Env-Var-Fallback entfernen; nur noch `load_settings().data_root` + Default
- [ ] `get_models_dir()`: liest `models_dir` aus `load_settings()` statt DB; `null` → Default
- [ ] `PHOTOFANT_DATA_ROOT`-Env-Var komplett entfernen

### `backend/photofant/api/config.py` umbauen

- [ ] `_read_config()`: liest von `load_settings()` statt DB; gibt alle Settings-Keys zurück
- [ ] `patch_config()`: schreibt via `patch_settings()` statt DB; Sonderbehandlung `models_dir` (Ordner anlegen) bleibt
- [ ] DB-Session-Dependency aus Config-Endpoints entfernen (nicht mehr nötig für Settings)

### App-Start

- [ ] `backend/photofant/main.py` (oder Lifespan-Hook): `ensure_settings_file()` aufrufen

### Repo

- [ ] **`settings.example.json`** im `backend/`-Verzeichnis mit allen Keys und ihren Defaults (Kommentare als separate `_comment_*`-Keys oder in separater Sektion — JSON hat keine Kommentare)
- [ ] **`.gitignore`** — ergänzen: `.photofant/settings.json` (projektweite `.gitignore` im Root)
- [ ] Doc-Update: `docs/routes.md` — `/api/config`-Endpoint-Notiz: "liest/schreibt settings.json"

## Report-Back
