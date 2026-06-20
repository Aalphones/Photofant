# P7 · Phase 4 — Personen-View

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (persons-Endpoints)
- [docs/design/README.md](../../design/README.md) — Personen-View; `docs/design/js/*` (Person-Card, Inline-Editor)

## Akzeptanzkriterien

- Personen-Grid nach Prototyp (Avatar-Kreise, Count, Hover-Ring); Avatar = bestes/gewähltes Face-Crop.
- Inline-Rename (Doppelklick/Long-Press), Import-Button auf der Karte, Drag & Drop von Dateien auf eine Karte → Import in den Person-Ordner (`fixed_person`).
- Klick auf Person → Galerie mit Person-Filter; Personen-Facette in der Rail + Person-Gruppierung im Grid werden aktiv.
- `persons`-NgRx-Slice; `_unknown` als eigene Karte („Unbekannt", nicht umbenennbar).

## Checkliste

- [x] `store/persons/` + PersonService
- [x] Personen-Grid + Person-Card (Avatar, Inline-Editor, Import-Button, DnD-Target)
- [x] Navigation Person → gefilterte Galerie; Rail-Facette + Gruppierung verdrahten
- [x] Framing-Heuristik-Nachtrag (BBox/Bild-Verhältnis → `asset.framing`, Rerun-Step `heuristics` erweitert) + Framing-Facette
- [x] Doc-Update: routes.md

## Report-Back

- `GET /api/persons` und `PATCH /api/persons/{id}` in `api/persons.py`; `PersonDto` mit `count`, `fav_count`, `portrait_face_id`.
- `Asset.framing` per BBox/Bild-Verhältnis: `heuristics_job._compute_framing()` (vorhandene Faces), `face_job._update_framing()` (nach Erkennung).
- NgRx-Slice `store/persons/` (actions, reducer, effects, selectors) + `PersonService` (`getPersons`, `renamePerson`, `portraitUrl`).
- `features/personen/` komplett: Grid-Host (`personen.ts/.html/.scss`) + `person-card/` (Avatar, Long-Press/Dblclick-Editor, Import-Button, DnD, Hidden-File-Input).
- `filtersActions.setPersonId` + `setFramings`; `gallery.selectors` nutzt `selectPersonNameMap` für Person-Gruppenname.
- Filter-Rail: Framing-Facette (Bildausschnitt-Accordion) eingebaut.
- Angular build: grün, keine neuen Fehler.
