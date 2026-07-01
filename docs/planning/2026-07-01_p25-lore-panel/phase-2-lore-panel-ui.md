# Phase 2 — Lore-Panel-UI (Lightbox-Kontextbereich)

**Komplexität:** heikel (Eingriff in P15-Screen + freihändiges Design) · **Status:** pending

## Kontext
- README → Design-Lage + **Screen-Eigentümer P15** + Chesterton
- **Zuerst lesen:** `../2026-06-28_p15-lightbox-angleichung/README.md` + `features/galerie/lightbox/` (Zoom-Stage, Panel-Header, Toolbar)
- Konzept Dok 050 §5/§13 · Phase 1: `GET .../lore` · `services/knowledge.service.ts` (P23)
- Bestand: `store/gallery/`, `mode-web-frontend`, `framework-tailwind`, `docs/design/styles.css`

## AK (UI-Struktur = Kontrakt)
- [ ] Bild öffnen → Panel lädt Lore (asset_id, bei Personenkontext person_id) und rendert Sektionen in dieser Reihenfolge: **Kurzbio · Rollen · Beziehungen · Franchises · Eigene Bilder · Quellen · Verwandte Entities** (Dok 050 §5). Leere Sektionen entfallen.
- [ ] Ohne Wissen: dezenter Zustand „Noch kein Wissen — anlegen?" mit Wizard-Absprung (P23).
- [ ] Beziehungs-/Verwandte-Einträge klickbar → Ziel-Entity.
- [ ] Dockt an P15s Panel-Struktur an (kein zweiter Container); P15-Zoom/Toolbar unverändert.
- [ ] Tailwind-Tokens, kein Chat.
- [ ] Lazy-Load: Lore erst bei offener Lightbox (UI blockiert nie).

## Umsetzung
- [ ] Lore-State (`store/gallery/` oder `store/knowledge/`, nach P15-Struktur — begründen)
- [ ] Lore-Panel-Komponente am P15-Andockpunkt + schlanke Sektions-Komponenten
- [ ] Leer-Zustand mit Wizard-Absprung
- [ ] Doc: `docs/code-map.md`, `docs/design-reconciliation.md` (freihändig markiert)
