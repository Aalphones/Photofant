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

- [x] Session-/Step-Endpoints + Render-Pipeline (Steps deterministisch aus Original + Param-Kette reproduzierbar)
- [x] `edit_step`-Handling in der Cache-DB (Preview-Erzeugung)
- [x] Editor-Route + Shell (Toolbar, Stage mit Zoom/Pan-Wiederverwendung aus Lightbox, Step-Leiste)
- [x] `store/editor/` + Öffnen-Einstiege (Lightbox „Bearbeiten", Bulk-Bar später)
- [x] Doc-Update: routes.md

## Report-Back

Phase abgeschlossen (2026-06-20). Alle AK erfüllt.
- Backend: `edit_session` + `edit_step` in Cache-DB; Endpoints `POST /edit-sessions`, `/steps`, `/rollback`, `GET /preview/{seq}`
- Render-Pipeline: Pillow (rotate/mirror/crop/pad/convert), Preview max 1024px, async via run_in_executor
- Frontend: NgRx-Slice `editor`, `EditSessionService`, Route `/editor/instance/:id` außerhalb Shell
- Editor-Shell mit BasisPanel (alle Stage-4-Basis-Ops), StepBar (History mit Previews), SaveModal
- Lightbox: „Bearbeiten"-Button öffnet Editor
- Commit: 15b3cc7
