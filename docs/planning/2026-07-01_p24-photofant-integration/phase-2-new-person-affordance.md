# Phase 2 — „Neue Person erkannt"-Affordance (UI)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Design-Lage + Screen-Eigentümer-Regel · Konzept Dok 050 §4/§13
- Phase 1: link-Routen, Trigger · **P23:** Wizard, Tasks, `features/wissen/`
- Bestand: `features/personen/`, `features/review/` (wahrscheinlichster Ort), `store/persons/`, `services/person.service.ts`

## AK
- [ ] Neu erkannte/bestätigte Person ohne Entity → dezenter Inline-Hinweis „🆕 Neue Person — Wissen anlegen?" mit drei Aktionen: **Wissen anlegen** (Wizard aus P23, Titel = Personenname vorbelegt), **Später** (Aufgabe bleibt offen), **Ignorieren** (dismissed).
- [ ] „Wissen anlegen" → nach Anlegen Person mit Entity verknüpft (Phase-1-Route), Hinweis weg.
- [ ] Kein Popup-Zwang — ruhiges Inline-Element, wegklickbar.
- [ ] Fügt sich in die Struktur des besitzenden Screens ein, kein Wegwerf-Container.

## Umsetzung
- [ ] Inline-Affordance in `features/review/` bzw. `features/personen/` (Bearbeiter wählt Screen, begründen)
- [ ] Verdrahtung: Wizard öffnen (Vorbelegung) → nach Success `link-entity` → Task resolve
- [ ] Store-Anbindung `store/persons/` + `store/knowledge/`
- [ ] Doc: `docs/code-map.md`
