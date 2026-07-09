# Phase 3 — Verknüpfte Entity an Person/Asset sichtbar (UI)

**Komplexität:** mechanisch (Anzeige eines vorhandenen DTO-Felds) · **Status:** complete

## Kontext
- README → Kontrakt (`linked_entity` aus Phase 1)
- Bestand: `features/personen/person-card/`, Asset-Detail lebt in `features/galerie/lightbox/` (kein eigener Detail-Ordner, anders als der Plan-Text unterstellt), `models/person.model.ts`, `models/asset.model.ts`

## AK
- [x] Personen-Karte zeigt bei Verknüpfung dezenten Entity-Chip (Titel + Typ); Klick → Wissens-Sicht.
- [x] Asset-Detail zeigt verknüpfte Entities analog.
- [x] Ohne Verknüpfung: kein Platzhalter, Element entfällt.
- [x] Vorhandene Chip/Badge-Tokens, kein neuer Stil.

## Umsetzung
- [x] `models/person.model.ts` + `models/asset.model.ts` um `linked_entity` (kein `?` — Backend liefert das Feld immer, Wert ist `null` statt fehlend)
- [x] Entity-Chip in `person-card` (Frosted-Glass-Stil wie `.person-card__np-btn`) + Lightbox (`.tag-chip`-Stil)
- [x] Klick-Navigation: `/wissen?entity=<id>` (Route aus P23) — siehe Deviations in der README, echte Entity-Detail-Ansicht kommt erst mit P25
- [x] Doc: `docs/code-map.md` nicht berührt — reine Logik-/UI-Ergänzung in bestehenden Dateien, keine neue Struktur
- [x] **Gesamt-P24:** finale AK + Smoke-Checkliste der README gegenprüfen
