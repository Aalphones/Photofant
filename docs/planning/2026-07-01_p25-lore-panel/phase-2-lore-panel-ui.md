# Phase 2 — Lore-Panel-UI (Lightbox-Kontextbereich)

**Komplexität:** heikel (Eingriff in P15-Screen + freihändiges Design) · **Status:** complete

> **Deviation (Sascha, 2026-07-09):** Statt der 7 Sektionen aus Dok 050 §5 gebaut als **5
> domänen-agnostische Sektionen** (Kurzbio · Beziehungen · Franchises · Eigene Bilder · Quellen).
> „Rollen"/„Verwandte Entitäten" entfallen als eigene Sektionen — ihre Info steckt in „Beziehungen"
> (nach Typ beschriftet). Grund: kein eigenes Datenfeld dafür; einzige Quelle wären die frei
> editierbaren Domänen-Beziehungstypen, die laut Domänen-Kontrakt nicht hart verdrahtet werden
> dürfen. Details in `docs/design-reconciliation.md` (Lightbox → Lore-Panel).

## Kontext
- README → Design-Lage + **Screen-Eigentümer P15** + Chesterton
- **Zuerst lesen:** `../2026-06-28_p15-lightbox-angleichung/README.md` + `features/galerie/lightbox/` (Zoom-Stage, Panel-Header, Toolbar)
- Konzept Dok 050 §5/§13 · Phase 1: `GET .../lore` · `services/knowledge.service.ts` (P23)
- Bestand: `store/gallery/`, `mode-web-frontend`, `framework-tailwind`, `docs/design/styles.css`

## AK (UI-Struktur = Kontrakt)
- [x] Bild öffnen → Panel lädt Lore (asset_id, bei Personenkontext person_id) und rendert Sektionen in dieser Reihenfolge: **Kurzbio · Beziehungen · Franchises · Eigene Bilder · Quellen** (5-Sektionen-Deviation, s.o.). Leere Sektionen entfallen.
- [x] Ohne Wissen: dezenter Zustand „Noch kein Wissen — anlegen" (nur bei Personenkontext) mit Absprung nach `/wissen` (Wizard liegt dort, P23).
- [x] Beziehungs-/Franchise-Einträge klickbar → `/wissen?entity=` (unaufgelöste Ziele mit leerem Typ nicht klickbar — Phase-1-Finding).
- [x] Dockt an P15s Panel-Struktur an (kein zweiter Container, `pf-lore-panel` als weitere `.panel-sec`); P15-Zoom/Toolbar unverändert.
- [x] Gleiche CSS-Tokens/Optik wie die Nachbar-Sektionen (P15 nutzt SCSS + CSS-Custom-Properties, kein Tailwind-Utility-Layer — an den Bestand angeglichen), kein Chat.
- [x] Lazy-Load: Lore lädt erst, wenn asset_id/person_id gesetzt ist (Lightbox offen); `catchError` degradiert still zum Leer-Zustand.

## Umsetzung
- [x] Lore-State direkt in `pf-lore-panel` via `toSignal` + `KnowledgeService.getLore` — **nach P15-Struktur** (Nachbarn `detail`/`lineage`/`relatedRail` laden genauso lokal per `toSignal`, kein NgRx-Slice), kein neuer Store nötig.
- [x] Lore-Panel-Komponente am P15-Andockpunkt (`lightbox.html` nach dem Panel-Header, beide Modi) + 5 Inline-Sektionen.
- [x] Leer-Zustand mit Absprung nach `/wissen`.
- [x] Doc: `docs/code-map.md`, `docs/design-reconciliation.md` (freihändig markiert)
