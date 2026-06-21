# P8 · Phase 2 — Geometrie-Operationen

> Rating: **heikel** (Crop-Canvas-Interaktion ist das komplexeste Frontend-Stück; Koordinaten-Mapping Stage↔Original) · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Ops + Params)
- [Konzept](../../Konzept-Photofant.md) §8.1 (Tabelle)
- `docs/design/js/editor-tools.jsx` (Crop-Interaktion als Verhaltens-Referenz)

## Akzeptanzkriterien

- Crop: freies Rechteck + fixe Ratios (1:1, 3:4, 16:9, …), Drag-Handles, Koordinaten korrekt vom gezoomten Stage-Raum in Original-Pixel gemappt (Rundung definiert).
- Pad-to-Square/Aspect (Randfarbe/transparent), Rotate (90°-Schritte + frei), Mirror (h/v), Convert (PNG↔JPEG, Quality-Slider, Alpha-Verlust-Warnung bei JPEG).
- Jede Op serverseitig in Pillow implementiert, Param-validiert; Preview < 1 s bei üblichen Größen (Preview auf verkleinerter Arbeitskopie rechnen, Final-Render in Originalauflösung beim Speichern).

## Checkliste

- [x] Pillow-Op-Module (crop/pad/rotate/mirror/convert) + Param-Schemas (pydantic)
- [x] Crop-Tool-Komponente (Handles, Ratio-Lock, Tastatur-Nudge)
- [x] Rotate/Mirror/Pad/Convert-Tool-Panels
- [x] Arbeitskopie-Strategie (Preview-Auflösung vs. Final-Render)
- [x] Doc-Update: routes.md Op-Param-Tabelle

## Report-Back

- `backend/photofant/media/ops.py`: Pydantic-validierte Op-Implementierungen (CropParams, RotateParams, MirrorParams, PadParams, ConvertParams) + Dispatcher `apply_op()`
- `edit_sessions.py`: `_render_steps` nutzt jetzt `apply_op()` aus ops.py; RGBA-Compositing nach Ende der Op-Pipeline (statt vor Ops), damit Pad-Transparent korrekt funktioniert
- `frontend/crop-overlay/`: Neue Komponente mit 8 Drag-Handles, Ratio-Lock, Keyboard-Nudge (Pfeiltasten ± Shift), box-shadow-basierte Dimming-Maske, image-bounds-Berechnung per ResizeObserver + Image.naturalWidth
- `basis-panel`: Erweitert um Pad-Aspect-Ratio (1:1, 4:3, 16:9, 3:2) + Farbwahl (Schwarz/Weiß/Transparent), Frei-Drehen-Slider (±180°), Crop-Mode-Toggle mit Aktivieren/Abbrechen
- `editor.ts`: Crop-State (cropActive, cropRect, cropRatio) als Signals; ZoomStage erhält `interactive`-Input (Zoom disabled bei aktivem Crop)
- `routes.md`: Op-Param-Tabelle mit Typen und Wertebereichen
