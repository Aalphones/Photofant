# Thumbnails · Phase 1 — Backend: THUMBNAIL_SIZES erweitern, thumbnail_quality entfernen

> Rating: **standard** · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, Größen-Mapping, Akzeptanzkriterien
- `backend/photofant/db/cache.py` — `THUMBNAIL_SIZES`
- `backend/photofant/api/assets.py` — `_VALID_THUMB_SIZES`, `get_asset_thumbnail()`
- `backend/photofant/jobs/thumbnail_job.py` — `generate_thumbnails()`
- `backend/photofant/settings.py` — `AppSettings`, `SETTINGS_DEFAULTS`
- `backend/.photofant/settings.json` — enthält noch toten `thumbnail_quality`-Key

## Akzeptanzkriterien

- Import generiert immer 256 + 512 + 1024 px.
- `GET /api/assets/{id}/thumbnail?size=1024` wird akzeptiert und liefert JPEG (on-demand-Fallback wenn nicht gecacht).
- `thumbnail_quality` ist aus `AppSettings`, `SETTINGS_DEFAULTS` und `settings.json` entfernt.

## Checkliste

- [x] **`cache.py`**: `THUMBNAIL_SIZES` von `(256, 512)` auf `(256, 512, 1024)` erweitern
- [x] **`assets.py`**: `_VALID_THUMB_SIZES` von `frozenset({256, 512})` auf `frozenset({256, 512, 1024})` erweitern
- [x] **`thumbnail_job.py`**: keine Änderung nötig — iteriert bereits über `THUMBNAIL_SIZES`; kurz verifizieren (Docstring auf "all THUMBNAIL_SIZES" aktualisiert)
- [x] **`settings.py`**: `thumbnail_quality`-Key aus `AppSettings` (TypedDict) und `SETTINGS_DEFAULTS` entfernen; aus `_EXPECTED_TYPES` entfernen
- [x] **`backend/.photofant/settings.json`**: toten `thumbnail_quality`-Key löschen
- [x] Doc-Update: `docs/routes.md` — `GET /api/assets/{id}/thumbnail` auf `size=256|512|1024` aktualisieren

## Report-Back
