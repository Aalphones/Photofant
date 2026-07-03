# Findings — P20 Virtual Scroll

Format: `- [ ] → Phase N: <Erkenntnis>`

- [x] → Phase 3 (erledigt): „Alle auswählen" hatte bisher einen Button pro
  Monatsgruppe (`.grid__month-head`), der mit den Gruppen weggefallen war —
  `GalerieGrid.onSelectAll()`/`selectAll`-Output waren unerreichbar (toter Pfad).
  Fix: neuer „Alle auswählen"-Button in der Sub-Toolbar (sichtbar bei aktivem
  Auswahlmodus), ruft direkt `allAssets()` im Parent (`galerie.ts`/`favoriten.ts`)
  ab. Grids `selectAll`-Output samt `onSelectAll()`-Methode entfernt (toter Code),
  beide Grid-Consumer (`galerie.html`, `favoriten.html`) umgestellt.
- [x] → Phase 3 (erledigt): `gallerySelectors.selectGroups`/`buildGroups`
  (`store/gallery/gallery.selectors.ts`) hatten keinen Consumer mehr — entfernt,
  inklusive der nur dafür existierenden `selectPersonNameMap`/`formatMonthLabel`.
- [x] → Phase 3 (erledigt, während der Recherche zum obigen Punkt entdeckt):
  Der „Gruppierung"-Button in der Sub-Toolbar (`cycleGroup()`) änderte nach dem
  Wegfall der Gruppen-Header nur noch unsichtbaren Store-Status
  (`filtersFeature.selectGroup`) und löste einen wirkungslosen Refetch aus —
  vorgetäuschte Funktion, kein P20-Plan-Scope. Dem User zur Entscheidung
  vorgelegt (Entscheidungsblock), Antwort: jetzt entfernen. Kaskadiert entfernt:
  Button + `GROUPS`/`cycleGroup`/`groupLabel` in `sub-toolbar.ts`/`.html`,
  `filtersActions.setGroup`, `FiltersState.group`, `filtersSelectors.group`,
  der `setGroup`-Eintrag in `gallery.effects.ts`s `onFiltersChange$`, sowie die
  Typen `GroupKey`/`GROUP_KEYS` und das nie konsumierte `AssetGroup` aus
  `models/asset.model.ts`. Details: ADR-011.
- [x] → Phase 2 (erledigt, informativ für Phase 3/ADR): `injectVirtualizer`s
  echte Angular-Wrapper-API nimmt `scrollElement: ElementRef | Element` direkt
  entgegen, **nicht** `getScrollElement: () => …` wie der Plan-Snippet (React-Doku-Stil)
  annahm. Umgesetzt mit der echten API (`scrollElement: this.scrollEl()`).
- [x] → Phase 2 (erledigt): `useApplicationRefTick: true` (Default) kollidierte
  mit dem eigenen Pagination-`effect()` — `NG0101: ApplicationRef.tick is called
  recursively`. Fix: `useApplicationRefTick: false` in den `injectVirtualizer`-Options
  (Angulars eigene Signal-Reaktivität reicht, da `getTotalSize()`/`getVirtualItems()`/
  `range()` bereits als Signals gelesen werden).
- [x] → Phase 3 (informativ): `favoriten.ts`/`.html`/`.scss` sind ein zweiter
  Consumer von `GalerieGrid`, den der Plan nicht auf dem Schirm hatte — wurde in
  Phase 2 mitgezogen (gleiche `assets`/`hasMore`-Inputs, gleiche Scroll-Höhenkette).
  `face-grid.scss` brauchte zusätzlich `:host{height:100%;overflow-y:auto}`, weil
  es vorher implizit am Shell-Level mitgescrollt ist und durch die neue
  Höhenkette sonst abgeschnitten worden wäre.
