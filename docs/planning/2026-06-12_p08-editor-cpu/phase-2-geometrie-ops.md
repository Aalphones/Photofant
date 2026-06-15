# P8 · Phase 2 — Geometrie-Operationen

> Rating: **heikel** (Crop-Canvas-Interaktion ist das komplexeste Frontend-Stück; Koordinaten-Mapping Stage↔Original) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Ops + Params)
- [Konzept](../../Konzept-Photofant.md) §8.1 (Tabelle)
- `docs/design/js/editor-tools.jsx` (Crop-Interaktion als Verhaltens-Referenz)

## Akzeptanzkriterien

- Crop: freies Rechteck + fixe Ratios (1:1, 3:4, 16:9, …), Drag-Handles, Koordinaten korrekt vom gezoomten Stage-Raum in Original-Pixel gemappt (Rundung definiert).
- Pad-to-Square/Aspect (Randfarbe/transparent), Rotate (90°-Schritte + frei), Mirror (h/v), Convert (PNG↔JPEG, Quality-Slider, Alpha-Verlust-Warnung bei JPEG).
- Jede Op serverseitig in Pillow implementiert, Param-validiert; Preview < 1 s bei üblichen Größen (Preview auf verkleinerter Arbeitskopie rechnen, Final-Render in Originalauflösung beim Speichern).

## Checkliste

- [ ] Pillow-Op-Module (crop/pad/rotate/mirror/convert) + Param-Schemas (pydantic)
- [ ] Crop-Tool-Komponente (Handles, Ratio-Lock, Tastatur-Nudge)
- [ ] Rotate/Mirror/Pad/Convert-Tool-Panels
- [ ] Arbeitskopie-Strategie (Preview-Auflösung vs. Final-Render)
- [ ] Doc-Update: keiner über routes.md hinaus

## Report-Back
