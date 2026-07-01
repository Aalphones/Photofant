# Phase 2 — Empfehlungs-Karten-UI (unter Lore Panel)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Design-Lage + Screen-Eigentümer (P15/P25) · Konzept Dok 050 §6/§13
- Phase 1: `GET /api/recommendations` · **P25:** Lore-Panel-Struktur (Andockort)
- Bestand: `store/gallery/`, Grid-/Cell-Muster `features/galerie/`, Tokens

## AK (UI-Struktur = Kontrakt)
- [ ] Unter dem Lore Panel (P25) ein Empfehlungs-Bereich mit Karten: **Vorschaubild · Score · Reason-Checkliste** (✓-Liste der Signale, Dok 050 §6).
- [ ] Karten-Klick öffnet das empfohlene Bild (bestehende Navigation).
- [ ] „Wird berechnet"-Status (leerer Cache) dezent, lädt nach Job-Ende nach (SSE/Poll wie andere Jobs).
- [ ] Keine Empfehlungen → Bereich entfällt.
- [ ] Dockt unter P25s Panel an, baut dessen Struktur nicht um.

## Umsetzung
- [ ] Reco-State (`store/gallery/` oder `store/knowledge/`, konsistent zu P25 — begründen)
- [ ] `services/` um Reco-Calls
- [ ] Empfehlungs-Karten-Komponente + Reason-Checklisten-Element
- [ ] „Wird berechnet"-Zustand + Nachladen
- [ ] Doc: `docs/code-map.md`, `docs/design-reconciliation.md` (freihändig markiert)
