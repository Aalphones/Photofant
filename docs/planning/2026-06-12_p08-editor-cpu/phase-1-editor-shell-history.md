# P8 · Phase 1 — Editor-Shell & Step-History

> Rating: **heikel** (Session-/History-Architektur trägt den ganzen Plan; Cache-DB-Semantik) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Session, Steps, Rollback)
- [Konzept](../../Konzept-Photofant.md) §5 (edit_step in der Cache-DB), **§8.2a komplett**
- `docs/design/js/editor.jsx`, `editor-store.js`, `docs/design/editor.css`

## Akzeptanzkriterien

- Editor-View nimmt den vollen Viewport ein (eigene Route, kein App-Shell); Werkzeugleiste, Stage, Step-Leiste (History mit Previews) nach Prototyp.
- Backend-Session: Steps werden serverseitig gerechnet (Pillow), als `edit_step` (op, params, preview-BLOB) in der Cache-DB versioniert; aktueller Zwischenstand als Temp-Render abrufbar.
- Rollback auf beliebigen `seq` (History dahinter wird bei neuem Step abgeschnitten — klassisches Undo-Branching vermeiden, linear halten).
- `editor`-NgRx-Slice: Session, Steps, aktueller Stand — temporär, wird beim Verlassen verworfen (Konzept §15).
- Verlassen ohne Speichern: Dialog nur, wenn ungespeicherte Steps existieren; History bleibt in der Cache-DB (Wiedereinstieg möglich).

## Checkliste

- [ ] Session-/Step-Endpoints + Render-Pipeline (Steps deterministisch aus Original + Param-Kette reproduzierbar)
- [ ] `edit_step`-Handling in der Cache-DB (Preview-Erzeugung)
- [ ] Editor-Route + Shell (Toolbar, Stage mit Zoom/Pan-Wiederverwendung aus Lightbox, Step-Leiste)
- [ ] `store/editor/` + Öffnen-Einstiege (Lightbox „Bearbeiten", Bulk-Bar später)
- [ ] Doc-Update: routes.md

## Report-Back
