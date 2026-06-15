# P2 · Phase 4 — Lightbox & Detail

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (`/file`-Endpoint)
- [docs/design/README.md](../../design/README.md) — Lightbox-Sektion; `docs/design/js/detail.jsx` als Verhaltens-Referenz
- [Konzept](../../Konzept-Photofant.md) §10 (Detailansicht)

## Akzeptanzkriterien

- Overlay mit Scrim + 2-Spalten-Layout (Stage + 372 px Panel) nach Prototyp.
- Zoom/Pan: Mausrad (1.2×/Step), Doppelklick (2.6×), Drag, max 6×, Zoom-Pill; Touch-Pinch.
- Navigation ←/→ durch die aktuelle gefilterte+sortierte Reihenfolge (über Seitengrenzen hinweg — lädt nach).
- Panel-Sektionen Stage-1-Umfang: Aktionen (Download), Metadaten-KV, Generation-Meta-Viewer (formatiert + Roh-JSON ausklappbar). Tags/Caption/Faces/Versionen-Sektionen als leere Struktur vorbereitet, ausgeblendet bis P5/P7/P8.

## Akzeptanz-Hinweis

Generation-Meta-Viewer: ComfyUI-Workflows sind verschachteltes JSON — Prompt/Seed/Steps/Model heuristisch extrahieren und als KV zeigen, Rest hinter „Details". Kein Parser-Perfektionismus; unbekanntes Format → Roh-Ansicht.

## Checkliste

- [ ] Lightbox-Feature (Overlay, Stage mit Zoom/Pan-Direktive, Nav-Buttons, Keyboard-Handling)
- [ ] Detail-Panel: KV-Grid (Dimensionen, Größe, Format, Datum, Quelle, Hash), Generation-Meta-Sektion
- [ ] Lightbox-State (geöffnete Id + Order) im gallery-Slice; Nachladen bei Navigation über Seitengrenze
- [ ] Download-Action (`/file`)
- [ ] Doc-Update: docs/routes.md ergänzen

## Report-Back
