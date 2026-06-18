# Einstellungen Thumbnail-Qualität · Phase 1 — Backend: thumbnail_quality config-Key

> Rating: **standard** · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, Größen-Mapping, Akzeptanzkriterien
- `backend/photofant/api/config.py` — `_read_config()`, `patch_config()`
- `backend/photofant/db/cache.py` — `THUMBNAIL_SIZES`
- `backend/photofant/api/assets.py` — `_VALID_THUMB_SIZES`, `get_asset_thumbnail()`
- `backend/photofant/jobs/thumbnail_job.py` — `generate_thumbnails()`, `enqueue_thumbnails()`

## Akzeptanzkriterien

- `GET /api/config` liefert `thumbnail_quality: "sm" | "md" | "lg"` (Default: `"md"` wenn nicht in settings.json).
- `PATCH /api/config` mit `{ "data": { "thumbnail_quality": "lg" } }` schreibt in `settings.json` (via `patch_settings()` aus Infrastruktur-Plan).
- `GET /api/assets/{id}/thumbnail?size=1024` wird akzeptiert und liefert JPEG (generiert on-demand wenn nicht gecacht).
- `thumbnail_job.py` generiert beim Import die der `thumbnail_quality` entsprechenden Größen statt der hardkodierten `(256, 512)`.
- Rückwärtskompatibel: bestehende Caches mit 256 + 512 bleiben gültig; keine Zwangsmigration.

## Checkliste

- [ ] **`settings.py` `AppSettings`** (aus Infrastruktur-Plan): `thumbnail_quality`-Key mit Default `"md"` ergänzen (in `AppSettings`-Dataclass + `SETTINGS_DEFAULTS`)
- [ ] **`cache.py`**: Hilfsfunktion `thumbnail_sizes_for_quality(quality: str) -> tuple[int, ...]` — Mapping sm/md/lg → Pixel-Tupel; `THUMBNAIL_SIZES` Konstante bleibt für Rückwärtskompatibilität als `md`-Default
- [ ] **`assets.py`**: `_VALID_THUMB_SIZES` von `frozenset({256, 512})` auf `frozenset({256, 512, 1024})` erweitern — Endpoint akzeptiert alle drei, generiert on-demand wenn nicht gecacht
- [ ] **`thumbnail_job.py`**: `generate_thumbnails()` und `run_thumbnail_job()` nehmen optionalen `sizes`-Parameter; Callers (Import-Pipeline) lesen `thumbnail_quality` aus Config und übergeben die entsprechenden Sizes — `THUMBNAIL_SIZES` als Fallback beibehalten
- [ ] Caller identifizieren: `grep -r "enqueue_thumbnails\|run_thumbnail_job"` im Backend — alle Aufrufstellen auf Config-Größen umstellen
- [ ] Doc-Update: `docs/routes.md` — `thumbnail_quality`-Key in der Config-Tabelle ergänzen

## Report-Back
