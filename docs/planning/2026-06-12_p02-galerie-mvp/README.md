# P2 — Galerie-MVP (Stage 1)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §18 Stage 1 · Abhängigkeiten: P1

Funktionierender lokaler Foto-Viewer ohne ML: Import mit Hash-Dedupe, Thumbnail-Cache, justiertes Grid, Lightbox, Favoriten als physischer Move, Papierkorb, Shortcuts.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Schema & Import-Backend](phase-1-schema-und-import.md) | standard | complete |
| 2 | [Thumbnail-Cache](phase-2-thumbnails.md) | standard | complete |
| 3 | [Galerie-Grid](phase-3-galerie-grid.md) | standard | complete |
| 4 | [Lightbox & Detail](phase-4-lightbox-detail.md) | standard | complete |
| 5 | [Favoriten & Papierkorb](phase-5-favoriten-papierkorb.md) | heikel | complete |
| 6 | [Import-UI & Shortcuts](phase-6-import-ui-shortcuts.md) | standard | complete |

## Kontrakt (Backend ↔ Frontend)

- **`GET /api/assets`** — Query: `page`, `page_size`, `sort` (`date|size`), `order` (`asc|desc`), `favourite` (bool, optional) → `{ items: AssetDto[], total, page, page_size }`
- **`AssetDto`:** `{ id, content_hash, width, height, file_size, format, source, created_at, imported_at, favourite, version_count, generation_meta }` — Erweiterung um Tags/Caption/Faces erfolgt in P5/P7 additiv (nie umbenennen).
- **`GET /api/assets/{id}`** — Detail (wie Dto, plus Pfad-Info).
- **`GET /api/assets/{id}/thumbnail?size=256|512`** — Bild-Response aus `thumbnails.sqlite`, `Cache-Control` + `ETag` über `content_hash`.
- **`GET /api/assets/{id}/file`** — Vollbild (Original) für die Lightbox.
- **`POST /api/assets/import`** — `{ paths: string[] }` (Server-seitige Pfade) bzw. Multipart-Upload → startet Queue-Job, Response `{ job_id }`.
- **`POST /api/assets/scan`** — FS-Scan auf neue Dateien → `{ job_id }`.
- **`PATCH /api/assets/{id}/favourite`** — `{ value: bool }` → physischer Move photos/↔favourites/, Response aktualisiertes Dto.
- **`DELETE /api/assets/{id}`** → Soft-Delete (Papierkorb). **`GET /api/trash`**, **`POST /api/trash/{id}/restore`**, **`DELETE /api/trash/{id}`** (endgültig).
- **Job-Kinds:** `import`, `scan`, `thumbnail` — Fortschritt über den bestehenden SSE-Stream.
- **Stage-1-Vereinfachung:** alles liegt unter `Data/_unknown/` (Personen gibt es erst in P7); `asset_instance` wird trotzdem von Anfang an angelegt (eine Instanz, Person `_unknown`), damit P7 keine Migration der Semantik braucht.

## Finale Akzeptanzkriterien

1. Ordner mit ≥1000 Bildern importieren → Fortschritt im Job-Dock, danach vollständig im Grid; erneuter Import derselben Dateien erzeugt keine Duplikate (Content-Hash).
2. Grid lädt seitenweise nach (Pagination), gruppiert nach Monat, drei Dichte-Stufen, Brick-Layout wie Prototyp.
3. Lightbox: Zoom (Rad/Doppelklick, max 6×), Pan, Pfeil-Navigation in Filter-Reihenfolge, Metadaten-Panel inkl. Generierungs-Meta bei AI-Bildern.
4. Favorit setzen/entfernen verschiebt die Datei physisch und überlebt einen Backend-Neustart konsistent (DB-Pfad stimmt).
5. Löschen → Papierkorb (Datei in `.photofant/trash/`), Wiederherstellen und endgültiges Löschen funktionieren über die UI.
6. Tastatur: ←/→ (Lightbox), F (Favorit), Entf (Papierkorb), Esc; Shortcut-Legende als Overlay (`?`).

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Echten Bilder-Ordner (gemischt PNG/JPEG, einige mit ComfyUI/A1111-Metadaten) importieren → alles sichtbar, AI-Bilder zeigen Quelle-Badge
- [ ] Selben Ordner nochmal importieren → Anzahl unverändert
- [ ] Favorit togglen → Datei liegt physisch in `favourites/`, UI-Stern an
- [ ] Bild löschen → in `Data/` weg, im Papierkorb sichtbar → wiederherstellen → wieder da
- [ ] Backend killen + neu starten → Grid identisch (DB konsistent)

## Summary

P2 Galerie-MVP abgeschlossen: lokaler Foto-Viewer ohne ML. Import mit Content-Hash-Dedupe, Thumbnail-Cache, justiertes Brick-Grid (3 Dichte-Stufen), Lightbox mit Zoom/Pan, Favoriten (physischer Move), Papierkorb mit Restore/Purge, Import-Dialog + globale DnD, Shortcut-Legende, Empty-State.

## Files touched

Backend: `photofant/api/assets.py`, `photofant/jobs/import_job.py`, `photofant/jobs/thumbnail_job.py`, `photofant/api/trash.py`, `photofant/media/moves.py`, `photofant/media/meta.py`, `photofant/media/thumbnails.py`, `pyproject.toml`

Frontend: `shell/`, `features/galerie/` (inkl. Lightbox, Grid, Cell, SubToolbar, Papierkorb), `ui/` (Icon, JobPill, JobDock, ImportDialog, ShortcutLegend), `services/` (AssetService, JobsService, ShortcutService), `store/` (gallery, filters, jobs, trash), `models/`

Docs: `routes.md`, `docs/planning/2026-06-12_p02-galerie-mvp/`

## Deviations from plan

- `/api/assets/upload` als separater Endpunkt statt multipart auf `/api/assets/import` (FastAPI-Limitation: Form-Data und JSON-Body nicht mischbar auf einer Route). Kontrakt-Semantik identisch.

## Follow-ups

- Animierte Spinner im Import-Dialog wären nice-to-have
- Import-Dialog: Ordner-Browse-Dialog wäre komfortabler als manuelle Pfadeingabe (Browser-Security-Limitation auf Desktop-App-Level lösbar via Tauri/Electron)
- ShortcutService: weitere Shortcuts (Galerie-Level, Bulk-Aktionen) in P-späteren Phasen registrieren
