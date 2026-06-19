# Phase 6 — Frontend: Lightbox + Action-Bar

## Design-Referenz

Kein eigenes Mockup für diese Entry Points → freihändig nach Konzept; AK beschreiben die Struktur.

## Kontext (vor Implementierung lesen)

- `docs/planning/2026-06-19_duplikaterkennung/README.md` — API-Kontrakt: `GET /api/assets/{id}/similar`
- `frontend/src/app/features/galerie/lightbox/lightbox.ts` — bestehende Lightbox
- `frontend/src/app/` — bestehende Action-Bar / Bulk-Aktionen (Struktur herausfinden)
- `docs/conventions/angular.md` + `docs/conventions/ngrx.md`

## Akzeptanzkriterien

### Lightbox

1. Lightbox-Toolbar enthält neuen Button "Ähnliche Bilder" (Icon: compare / link; nur sichtbar wenn das Asset einen pHash hat).
2. Klick lädt `GET /api/assets/{id}/similar` → Ergebnis-Overlay öffnet sich innerhalb der Lightbox (kein Page-Navigation).
3. Overlay zeigt: horizontale Thumbnail-Leiste der ähnlichen Assets mit Ähnlichkeitswert (0–63 Hamming → visuell als Balken oder Prozent-Ähnlichkeit).
4. Klick auf ein ähnliches Asset öffnet die Compare-Ansicht (kann `pf-dupe-compare` aus Phase 5 wiederverwenden) mit den 4 Aktionen.
5. Ist das Asset ohne pHash (pHash=NULL), ist der Button ausgegraut mit Tooltip "Noch nicht analysiert".

### Action-Bar (Bulk)

6. Sind ≥2 Assets selektiert: Action-Bar zeigt Aktion "Duplikate prüfen".
7. Klick triggert `POST /api/jobs/dupe-scan` mit `{ scope: 'selection', asset_ids: [...] }`.
8. Toast: "Duplikat-Scan für N Bilder gestartet" + Link zur Review-Queue.
9. Navigation zur Review-Queue erfolgt **nicht** automatisch — nur der Toast-Link ist optional.

## Checkliste

### Lightbox

- [ ] `lightbox.ts` — Button "Ähnliche Bilder" in Toolbar einbauen (Signal `hasPHash` aus Asset-Daten)
- [ ] Effect / Service-Call: `GET /api/assets/{id}/similar` bei Klick
- [ ] Overlay-State in Lightbox-Komponente: `similarAssets: SimilarAsset[]`, `showSimilar: boolean`
- [ ] Overlay-Template: Thumbnail-Leiste + Ähnlichkeitswert; Klick öffnet `pf-dupe-compare` (Phase 5 wiederverwenden)
- [ ] Ausgegrayten Button-Zustand für pHash=NULL implementieren

### Action-Bar

- [ ] Bestehende Bulk-Aktionen-Komponente öffnen; Aktion "Duplikate prüfen" ergänzen (ab 2 selektierten Assets)
- [ ] `triggerDupeScan` Action dispatchen mit `scope: 'selection'` + `asset_ids`
- [ ] Toast einblenden (bestehende Toast-Infrastruktur nutzen)

### Docs

- [ ] `docs/routes.md` — `GET /api/assets/{id}/similar` sollte bereits in Phase 3 eingetragen sein; prüfen

## Report-Back
