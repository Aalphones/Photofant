# Thumbnails — Dreifache Größen (256 / 512 / 1024 px)

> Status: pending

Immer alle drei Thumbnail-Größen generieren und cachen. Keine konfigurierbare "Qualitätsstufe" mehr — die Dichte-Einstellung in der Galerie steuert nur, welche gecachte Größe angefragt wird.

**Kern-Unterschied zu heute:**
| Aspekt | Heute | Nach dem Plan |
|---|---|---|
| Generierungsgrößen | fest (256, 512 px) | immer (256, 512, 1024 px) |
| `thumbnail_quality`-Setting | in settings.json, aber toter Code | entfernt |
| Gallery-Cell fragt an | immer 256 px (hartkodiert) | sm→256, md→512, lg→1024 |
| 1024-px-Thumbnails | nicht vorhanden | immer gecacht |

**Density → Thumbnail-Mapping:**
| Density | Zellhöhe | Thumbnail-Größe |
|---|---|---|
| `sm` | 150 px | 256 px |
| `md` | 196 px | 512 px |
| `lg` | 250 px | 1024 px |

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Backend: THUMBNAIL_SIZES erweitern, thumbnail_quality entfernen](phase-1-backend-config.md) | standard | complete |
| 2 | [Frontend: Cell fragt Größe nach Density an](phase-2-frontend-wiring.md) | standard | pending |
| 3 | [Rebuild-Job: 1024-px-Lücke bei bestehenden Assets füllen](phase-3-rebuild-cache.md) | heikel | pending |

## Kontrakt (Backend ↔ Frontend)

### Thumbnail-Endpoint
- **`GET /api/assets/{id}/thumbnail?size=256|512|1024`** — alle drei Größen gültig; on-demand-Fallback wenn nicht gecacht (lazy, immer korrekt)

### Rebuild-Job (Phase 3)
- **`POST /api/maintenance/rebuild-thumbnails`** — generiert für alle Assets fehlende Größen (skip-if-exists); Response `{ job_id }`
- Fortschritt über SSE-Jobs-Stream (`GET /api/jobs/stream`)

## Finale Akzeptanzkriterien

1. Import generiert immer 256 + 512 + 1024 px und legt sie in die Cache-DB.
2. `GET /api/assets/{id}/thumbnail?size=1024` liefert JPEG (lazy fallback wenn nicht gecacht).
3. Gallery-Cell fordert bei `sm`→256, `md`→512, `lg`→1024 an — sichtbarer Schärfeunterschied.
4. `thumbnail_quality` ist aus `settings.json` und der Einstellungen-UI entfernt.
5. Rebuild-Job über Wartung-UI startbar; füllt fehlende 1024-px-Einträge für bestehende Assets.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Neues Bild importieren → `thumbnails.sqlite` enthält Einträge für 256, 512 und 1024 px
- [ ] `GET /api/assets/1/thumbnail?size=1024` → liefert JPEG
- [ ] Galerie-Dichte auf `lg` → Thumbnails sichtbar schärfer als bei `md`
- [ ] Galerie-Dichte auf `sm` → 256-px-Request im Browser-DevTools Network-Tab sichtbar
- [ ] Rebuild-Job starten → Job-Dock zeigt Fortschritt → `thumbnails.sqlite` enthält 1024-px-Einträge für Bestandsbilder
- [ ] `settings.json` enthält kein `thumbnail_quality` mehr

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups

- Disk-Usage-Anzeige in Einstellungen (Bibliothek-Sektion) könnte Thumbnail-Cache-Größe anzeigen.
- Eviction-Policy für 1024-px-Einträge nach Rebuild (kein Datenverlust, bewusst ausgeklammert).
