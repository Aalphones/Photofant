# P20 — Virtual Scroll in der Galerie

**Datum:** 2026-06-30
**ADR:** 011 (wird in Phase 3 angelegt)

## Überblick

| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | [Row-Breaking-Engine](phase-1-layout-engine.md) | heikel | done |
| 2 | [@tanstack/angular-virtual Integration](phase-2-virtual-rendering.md) | heikel | done |
| 3 | [Polish & ADR](phase-3-polish-adr.md) | standard | done |

## Scope & Designentscheidungen

**Monatsgruppen entfallen.** Die Galerie zeigt Assets als flache, fortlaufende Zeilen.
Keine Group-Header mehr, kein `selectGroups`-Selektor im Grid.

**@tanstack/angular-virtual** übernimmt das DOM-Rendering.
Die Row-Breaking-Engine (Phase 1) liefert ihm die flache `VirtualRow[]`-Liste.

**Paginierung bleibt store-seitig unverändert.**
Virtual Scroll steuert nur den DOM — nicht das Datenfetching.
Wenn der Virtualizer das Ende der geladenen Rows erreicht, dispatcht ein `effect`
`galleryActions.requestNextPage()` (wie heute der Sentinel, nur anders getriggert).

## Kontrakt (Phase 1 → Phase 2)

```typescript
// row-layout.ts — öffentliche API

interface LayoutItem {
  kind: 'asset' | 'face';
  id: number;
  ratio: number;    // Breite/Höhe; Faces = 1.0
  assetId?: number; // nur bei kind === 'face'
}

interface VirtualRow {
  items: LayoutItem[];
}

// buildLayoutItems: flache Liste aus Assets + interleaved Faces
function buildLayoutItems(
  assets: AssetDto[],
  facesMap: Map<number, FaceGalleryItemDto[]>
): LayoutItem[]

// computeRows: teilt die Items in Zeilen auf
function computeRows(
  items: LayoutItem[],
  containerWidth: number,
  baseHeight: number,
  gap: number
): VirtualRow[]

const GRID_GAP = 8;     // px, aus .grid__row { gap: 8px }
const GRID_PADDING = 16; // px einseitig, aus :host { padding: 0 16px }
```

Alle Zeilen haben Höhe `baseHeight` (uniform) — kein `measureElement` nötig.
Gap wird als Teil der Row-Höhe behandelt: `ROW_HEIGHT = baseHeight + GRID_GAP`.
(Letzter Gap im Grid spielt keine Rolle für die Scroll-Höhe.)

## Finale Abnahmekriterien

1. Galerie mit 500+ Assets: DevTools zeigt zu jedem Zeitpunkt ≤ `overscan * 2 + viewport_rows` `.grid__virtual-row`-Elemente im DOM.
2. Scrollen durch 6000 Assets: kein Layout-Sprung, kein Blank-Flash länger als ein Frame.
3. Am Ende geladener Assets angelangt → `requestNextPage` feuert, neue Assets erscheinen nahtlos darunter.
4. Scrollen zurück nach oben: kein Fetching, sofort gerendert (aus Store).
5. Shift-Klick Range-Select funktioniert über virtualisierten Bereich hinweg.
6. Bulk-Select „Alle auswählen" liefert alle geladenen IDs korrekt.

## Smoke-Checkliste (User prüft nach Abschluss)

- [ ] DevTools Elements: nur ~20–30 `.grid__virtual-row`-Divs im DOM, egal wie viele Assets geladen
- [ ] Schnell zum Ende scrollen → neue Bilder laden, Spinner erscheint, Bilder hängen sich an
- [ ] Zurückscrollen zum Anfang → erste Bilder da, kein Flicker, kein Netzwerk-Request
- [ ] Viewport verkleinern auf 800px → Rows umbrechen korrekt neu (mehr Zeilen)
- [ ] Shift-Klick Range-Select über sichtbare + off-screen Bilder → korrekte Anzahl IDs
- [ ] `ng test` läuft durch (falls Unit-Tests für row-layout.ts angelegt)

## Bottom Sections (beim Archivieren füllen)

### Summary

Galerie rendert jetzt virtualisiert (Row-level, `@tanstack/angular-virtual`) statt
alle Assets als DOM-Knoten zu halten — Monatsgruppen sind einer flachen,
fortlaufenden Liste gewichen. Phase 3 hat die Polish-Punkte geschlossen
(ResizeObserver-Debounce, Zero-Width-Guard) und zwei liegen gebliebene
UI-Lücken aus dem Umbau gefixt: „Alle auswählen" war unerreichbar geworden,
und der „Gruppierung"-Button täuschte nach dem Wegfall der Gruppen-Header eine
nicht mehr existierende Funktion vor — beide behoben, Details in FINDINGS.md
und ADR-011.

### Files touched

- `frontend/src/app/features/galerie/grid/{grid.ts,row-layout.ts}` — Virtualizer-Host + Row-Breaking-Engine (P20 Kern)
- `frontend/src/app/features/galerie/{galerie,favoriten,sub-toolbar}/*` — Select-All-Wiring, Gruppierung-Button entfernt
- `frontend/src/app/features/galerie/face-grid/*` — eigener Scroll-Container (Ripple-Effekt Phase 2)
- `frontend/src/app/store/gallery/gallery.selectors.ts` — `selectGroups`/`buildGroups` entfernt
- `frontend/src/app/store/filters/{filters.actions,filters.reducer,filters.selectors}.ts` — `group`-Filterstatus entfernt
- `frontend/src/app/store/gallery/gallery.effects.ts` — `setGroup` aus Refetch-Trigger entfernt
- `frontend/src/app/models/asset.model.ts` — `GroupKey`/`GROUP_KEYS`/`AssetGroup` entfernt
- `docs/decisions/011-galerie-virtual-scroll.md` — neu

### Commits

- `c612681` feat(galerie): row-breaking engine for virtual scroll (P20 phase 1)
- `76347ba` feat(frontend): virtualize gallery grid with @tanstack/angular-virtual (Phase 2/3 Ripple-Effekte)
- Phase-3-Commit: siehe `git log` (Polish, ADR-011, Gruppierung-Cleanup) — direkt nach diesem Archivieren

### Deviations from plan

- `favoriten.ts`/`.html`/`.scss` und `face-grid.scss` waren nicht im ursprünglichen
  Plan-Scope, wurden aber in Phase 2 mitgezogen (zweiter `GalerieGrid`-Consumer,
  gleiche Höhenkette) — siehe FINDINGS.md.
- Phase 3 hat zusätzlich zum Plan-Scope den toten „Gruppierung"-Button samt
  Store-Pfad entfernt (mit dem User abgestimmt, kein stiller Change) —
  siehe FINDINGS.md, ADR-011.

### Follow-ups

- `docs/decisions/012-galerie-stapel-flache-einzeleintraege.md` dokumentierte
  bereits zwei bekannte Lücken (Version-Favorit/-Löschen, Version-als-Workflow-Input) —
  unverändert offen, nicht P20-Scope.
- CSS-Budget `lightbox.scss` weiterhin über Soll (24.77 kB vs. 8 kB Komponenten-Budget) —
  vorbestehend, keine P20-Regression, unbehoben.
