# Einstellungen — Thumbnail-Qualität (konfigurierbar)

> Status: geparkt · Abhängigkeiten: keine (standalone) · Voraussetzung: Darstellung-Tab in Einstellungen (bereits gebaut, PR-Stand 2026-06-18)

Macht die Thumbnail-Generierungsgröße über die Einstellungen-UI konfigurierbar und verdrahtet sie durch Backend + Frontend. Bisher ist `THUMBNAIL_SIZES = (256, 512)` hartkodiert in `backend/photofant/db/cache.py` und `_VALID_THUMB_SIZES = {256, 512}` in `backend/photofant/api/assets.py`; der Darstellung-Tab im Frontend speichert die Dichte nur lokal (localStorage / NgRx-Session).

**Kern-Unterschied zu heute:**
| Aspekt | Heute | Nach dem Plan |
|---|---|---|
| Generierungsgrößen | fest (256, 512 px) | konfigurierbar (sm/md/lg) |
| Einstellung gespeichert | NgRx-Session + localStorage | Backend `app_config` DB |
| Sitzungsübergreifend persistent | nein | ja |
| 1024-px-Thumbnail möglich | nein | ja (bei `lg`) |

**Größen-Mapping:**
| Qualität | Generierte Größen | Wann sinnvoll |
|---|---|---|
| `sm` | 256 px | Nur Thumbnails, kein Lightbox-Zoom |
| `md` (Standard) | 256 + 512 px | Bisheriges Verhalten, Lightbox ok |
| `lg` | 256 + 512 + 1024 px | Hochauflösende Lightbox, mehr Disk |

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Backend: thumbnail_quality config-Key](phase-1-backend-config.md) | standard | pending |
| 2 | [Frontend: Config-Store + Einstellungen-Verdrahtung](phase-2-frontend-wiring.md) | standard | pending |
| 3 | [Rebuild-Job: Cache-Vorverdichtung](phase-3-rebuild-cache.md) | heikel | pending |

## Kontrakt (Backend ↔ Frontend)

### Konfiguration
- **`GET /api/config`** — liefert neu `thumbnail_quality: "sm" | "md" | "lg"` (Default: `"md"`)
- **`PATCH /api/config`** — `{ data: { thumbnail_quality: "lg" } }` speichert in `app_config`-Tabelle

### Thumbnail-Endpoint (Erweiterung)
- **`GET /api/assets/{id}/thumbnail?size=256|512|1024`** — `1024` wird neu zugelassen; wenn nicht gecacht, wird on-demand generiert (lazy fallback — immer korrekt, auch ohne vorherigen Rebuild)

### Rebuild-Job (neu, Phase 3)
- **`POST /api/maintenance/rebuild-thumbnails`** — liest aktuelle `thumbnail_quality` aus Config, queued einen Job der für alle Assets die fehlenden Größen generiert; Response `{ job_id }`
- Fortschritt über bestehenden SSE-Jobs-Stream (`GET /api/jobs/stream`)

## Finale Akzeptanzkriterien

1. `thumbnail_quality` in `app_config`-DB gespeichert, überlebt Backend-Neustart.
2. Thumbnail-Endpoint akzeptiert `?size=1024` und liefert korrekte JPEG-Antwort.
3. Frontend-Einstellungen zeigen den aktuellen Wert aus der Backend-Config; Änderung schreibt sofort via PATCH.
4. Nach Qualitätswechsel auf `lg`: Rebuild-Job über UI startbar; Fortschritt im Job-Dock sichtbar.
5. Lazy-Fallback: auch ohne Rebuild werden 1024-px-Thumbnails bei erstem Abruf generiert und gecacht.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Einstellung auf `lg` setzen → `app_config` per SQL oder GET /api/config prüfen → Wert `"lg"` persistent
- [ ] Backend neu starten → Einstellung bleibt `"lg"` (kein Reset auf Default)
- [ ] `GET /api/assets/1/thumbnail?size=1024` → liefert JPEG (ggf. kurze Wartezeit beim ersten Mal)
- [ ] Rebuild-Job starten → Job-Dock zeigt Fortschritt → nach Abschluss: `thumbnails.sqlite` enthält 1024-px-Einträge
- [ ] Einstellung auf `sm` zurück → `?size=512` antwortet weiterhin (bestehende Caches bleiben, kein Datenverlust)

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups

- Disk-Usage-Anzeige in Einstellungen (Bibliothek-Sektion) könnte nach Phase 3 um Thumbnail-Cache-Größe ergänzt werden.
- Eviction-Policy für nicht mehr benötigte Thumbnail-Größen (z.B. nach Wechsel `lg` → `sm`): bewusst ausgeklammert — kein Datenverlust, nur etwas mehr Disk.
