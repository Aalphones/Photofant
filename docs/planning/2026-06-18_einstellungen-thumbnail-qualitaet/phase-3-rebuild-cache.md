# Thumbnails · Phase 3 — Rebuild-Job: 1024-px-Lücke bei bestehenden Assets füllen

> Rating: **heikel** · Status: pending · Voraussetzung: Phase 1 + 2 abgeschlossen

## Kontext (vorher lesen)

- [README.md](README.md) — Smoke-Checkliste
- `backend/photofant/api/maintenance.py` — bestehende Maintenance-Endpoints
- `backend/photofant/jobs/thumbnail_job.py` — `enqueue_thumbnails`, `generate_thumbnails`
- `backend/photofant/db/cache.py` — `count_thumbnail_targets`, `clear_cache`
- `frontend/src/app/store/maintenance/` — bestehender Maintenance-Slice

## Warum heikel

- Rebuild läuft über **alle Assets** — bei großen Bibliotheken (10k+ Bilder) mehrere Minuten; muss robust sein (skip-if-exists, kein Clear davor)
- Partial-State während des Jobs: manche Assets haben 1024 px, andere noch nicht — lazy Fallback im Endpoint fängt das korrekt ab
- Falsches `clear_cache` vor Rebuild würde vorhandene 256/512-Thumbnails löschen → alle drei Größen für alle Assets neu generieren (unnötig teuer)

## Entscheidung (Scope dieses Plans)

**Additive Strategie** — niemals existierende Thumbnail-Größen löschen. Der Job generiert ausschließlich fehlende Größen (skip-if-exists). Nur die 1024-px-Lücke aus dem Bestand wird gefüllt; 256 und 512 sind bereits vorhanden.

## Akzeptanzkriterien

- `POST /api/maintenance/rebuild-thumbnails` startet einen Job der für alle aktiven Assets die **fehlenden** Sizes aus `THUMBNAIL_SIZES` generiert (also 1024 px für Bestandsbilder).
- Job erscheint im Job-Dock mit Fortschritt (% Bilder abgearbeitet).
- Gleichzeitig laufende Rebuilds werden abgelehnt (HTTP 409 + klare Fehlermeldung).
- Frontend: "Thumbnails neu generieren"-Button in der Wartung-UI.

## Checkliste

- [ ] **Backend `maintenance.py`**: neuer Endpoint `POST /api/maintenance/rebuild-thumbnails`
  - Ruft `enqueue_thumbnail_rebuild()` aus `thumbnail_job.py` auf
  - Prüft: läuft bereits ein `THUMBNAIL_REBUILD`-Job → HTTP 409
  - Response: `{ job_id }`
- [ ] **`thumbnail_job.py`**: neue Funktion `enqueue_thumbnail_rebuild()` / `run_thumbnail_rebuild_job()`
  - Lädt alle aktiven Asset-IDs + Pfade aus DB
  - Iteriert über alle Assets × `THUMBNAIL_SIZES`
  - Skip wenn `get_thumbnail(db, asset_id, size)` bereits existiert
  - Fortschritt via `job_queue.update()`
  - `JobKind.THUMBNAIL_REBUILD` ergänzen (oder bestehenden `THUMBNAIL`-Kind prüfen ob ausreichend)
- [ ] **`maintenance.model.ts`** (Frontend): `RebuildTarget` ggf. um `thumbnail_rebuild` ergänzen
- [ ] **`maintenance.actions.ts`**: `triggerThumbnailRebuild()` Action
- [ ] **`maintenance.effects.ts`**: Effect ruft `POST /api/maintenance/rebuild-thumbnails` auf
- [ ] **`maintenance.service.ts`**: Methode `rebuildThumbnails()` → HTTP-POST
- [ ] **`einstellungen.ts` / Wartung-UI**: Button "Thumbnails neu generieren"; disabled während Job läuft
- [ ] Doc-Update: `docs/routes.md` — neuen Endpoint dokumentieren

## Heikel: Was schiefgehen kann

| Risiko | Gegenmaßnahme |
|---|---|
| Job läuft Stunden, User schließt Browser | Job läuft serverseitig weiter; beim nächsten Start zeigt Job-Dock den laufenden Job |
| Disk läuft voll während Rebuild | `generate_thumbnail` schlägt mit `OSError` fehl → Warning-Log, Job fährt weiter |
| Asset-Pfad nicht mehr vorhanden | Warning-Log, überspringen (wie heute in `thumbnail_job.py`) |
| Mehrfach-Klick auf "Rebuild" | HTTP 409, Frontend zeigt Toast "Rebuild läuft bereits" |

## Report-Back
