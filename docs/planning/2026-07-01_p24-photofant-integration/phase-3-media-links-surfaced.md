# Phase 3 — Verknüpfte Entity an Person/Asset sichtbar (UI)

**Komplexität:** mechanisch (Anzeige eines vorhandenen DTO-Felds) · **Status:** pending

## Kontext
- README → Kontrakt (`linked_entity` aus Phase 1)
- Bestand: `features/personen/person-card/`, Asset-Detail in `features/galerie/`, `models/person.model.ts`, `models/asset.model.ts`

## AK
- [ ] Personen-Karte zeigt bei Verknüpfung dezenten Entity-Chip (Titel + Typ); Klick → Wissens-Sicht.
- [ ] Asset-Detail zeigt verknüpfte Entities analog.
- [ ] Ohne Verknüpfung: kein Platzhalter, Element entfällt.
- [ ] Vorhandene Chip/Badge-Tokens, kein neuer Stil.

## Umsetzung
- [ ] `models/person.model.ts` + `models/asset.model.ts` um `linkedEntity?`
- [ ] Entity-Chip in `person-card` + Asset-Detail
- [ ] Klick-Navigation zur Wissens-Sicht (Route aus P23)
- [ ] Doc: ggf. `docs/code-map.md`
- [ ] **Gesamt-P24:** finale AK + Smoke-Checkliste der README gegenprüfen
