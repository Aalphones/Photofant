# Einstellungen Thumbnail-Qualität · Phase 3 — Rebuild-Job: Cache-Vorverdichtung

> Rating: **heikel** · Status: pending · Voraussetzung: Phase 1 + 2 abgeschlossen

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, Smoke-Checkliste
- `backend/photofant/api/maintenance.py` — bestehende Maintenance-Endpoints (Rebuild-Targets, Repair-Jobs)
- `backend/photofant/jobs/thumbnail_job.py` — `enqueue_thumbnails`, `generate_thumbnails`
- `backend/photofant/db/cache.py` — `count_thumbnail_targets`, `clear_cache`
- `frontend/src/app/store/maintenance/` — bestehender Maintenance-Slice (triggerBackup, loadBackups)

## Warum heikel

- Rebuild läuft über **alle Assets** — bei großen Bibliotheken (10k+ Bilder) mehrere Minuten; muss robust pausierbar/fortführbar sein
- Partial-State während des Jobs: manche Assets haben 1024 px, andere noch nicht — Frontend muss das tolerieren (lazy fallback greift)
- Falsches `clear_cache` vor Rebuild würde vorhandene 256/512-Thumbnails löschen → alle Thumbnails regenerieren statt nur die fehlenden

## Entscheidung (Scope dieses Plans)

**Additive Strategie** — niemals existierende Thumbnail-Größen löschen. Der Job generiert ausschließlich fehlende Größen (Skip-if-exists). Beim Wechsel `lg → sm` bleibt der 1024-px-Cache erhalten (Disk-Overhead, aber kein Datenverlust, kein unnötiger Re-Compute).

## Akzeptanzkriterien

- `POST /api/maintenance/rebuild-thumbnails` startet einen Job der für alle aktiven Assets die **fehlenden** Sizes lt. aktuellem `thumbnail_quality` generiert.
- Job erscheint im Job-Dock mit Fortschritt (% Bilder abgearbeitet).
- Gleichzeitig laufende Rebuilds werden abgelehnt (HTTP 409 + klare Fehlermeldung).
- Einstellungen-UI: "Thumbnails neu generieren"-Button erscheint, wenn `thumbnail_quality` auf `lg` steht und 1024-px-Thumbnails noch nicht vollständig generiert wurden (einfache Heuristik: `thumbnail_quality = lg` AND `count_thumbnail_targets(size=1024) < total_assets`).
- Frontend dispatcht `maintenanceActions.triggerThumbnailRebuild()`, Effect ruft neuen Endpoint auf, Job-ID landet im Job-Store.

## Checkliste

- [ ] **Backend `maintenance.py`**: neuer Endpoint `POST /api/maintenance/rebuild-thumbnails`
  - Liest `thumbnail_quality` aus `app_config`
  - Ruft neues `enqueue_thumbnail_rebuild()` aus `thumbnail_job.py` auf
  - Prüft: läuft bereits ein `THUMBNAIL_REBUILD`-Job → HTTP 409
  - Response: `{ job_id }`
- [ ] **`thumbnail_job.py`**: neue Funktion `enqueue_thumbnail_rebuild()` / `run_thumbnail_rebuild_job()`
  - Lädt alle aktiven Asset-IDs + Pfade aus DB
  - Iteriert über alle Assets × alle Sizes lt. Config
  - Skip wenn `get_thumbnail(db, asset_id, size)` bereits existiert
  - Fortschritt via `job_queue.update()`
  - Neues `JobKind.THUMBNAIL_REBUILD` falls nötig (oder bestehenden `THUMBNAIL`-Kind wiederverwenden — ADR-Entscheidung vor Impl)
- [ ] **`maintenance.models.ts`** (Frontend-Modelle): `RebuildTarget` ggf. um `thumbnail_rebuild` ergänzen (checken ob schon vorhanden in `maintenance.model.ts`)
- [ ] **`maintenance.actions.ts`**: `triggerThumbnailRebuild()` Action
- [ ] **`maintenance.effects.ts`**: Effect ruft `POST /api/maintenance/rebuild-thumbnails` auf, dispatcht `triggerBackupSuccess` oder einen neuen `triggerThumbnailRebuildSuccess`-Action mit `{ jobId }`
- [ ] **`maintenance.service.ts`**: Methode `rebuildThumbnails()` → HTTP-POST
- [ ] **`einstellungen.ts`**: Hinweis + Button "Thumbnails neu generieren" wenn Bedingung erfüllt (s.o.); dispatcht `maintenanceActions.triggerThumbnailRebuild()`; Button disabled während Job läuft
- [ ] Doc-Update: `docs/routes.md` — neuen Endpoint dokumentieren

## Heikel: Was schiefgehen kann und wie damit umgehen

| Risiko | Gegenmaßnahme |
|---|---|
| Job läuft Stunden, User schließt Browser | Job läuft serverseitig weiter; beim nächsten Start zeigt Job-Dock den laufenden Job |
| Disk läuft voll während Rebuild | `generate_thumbnail` schlägt mit `OSError` fehl → Warning-Log, Job fährt weiter, Fehler-Count in Job-Summary |
| Asset-Pfad nicht mehr vorhanden | Wie heute in `thumbnail_job.py`: Warning-Log, überspringen |
| Mehrfach-Klick auf "Rebuild" | HTTP 409 vom Backend, Frontend zeigt Toazt "Rebuild läuft bereits" |

## Report-Back
