# P7 · Phase 4 — Personen-View

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (persons-Endpoints)
- [docs/design/README.md](../../design/README.md) — Personen-View; `docs/design/js/*` (Person-Card, Inline-Editor)

## Akzeptanzkriterien

- Personen-Grid nach Prototyp (Avatar-Kreise, Count, Hover-Ring); Avatar = bestes/gewähltes Face-Crop.
- Inline-Rename (Doppelklick/Long-Press), Import-Button auf der Karte, Drag & Drop von Dateien auf eine Karte → Import in den Person-Ordner (`fixed_person`).
- Klick auf Person → Galerie mit Person-Filter; Personen-Facette in der Rail + Person-Gruppierung im Grid werden aktiv.
- `persons`-NgRx-Slice; `_unknown` als eigene Karte („Unbekannt", nicht umbenennbar).

## Checkliste

- [ ] `store/persons/` + PersonService
- [ ] Personen-Grid + Person-Card (Avatar, Inline-Editor, Import-Button, DnD-Target)
- [ ] Navigation Person → gefilterte Galerie; Rail-Facette + Gruppierung verdrahten
- [ ] Framing-Heuristik-Nachtrag (BBox/Bild-Verhältnis → `asset.framing`, Rerun-Step `heuristics` erweitert) + Framing-Facette
- [ ] Doc-Update: routes.md

## Report-Back
