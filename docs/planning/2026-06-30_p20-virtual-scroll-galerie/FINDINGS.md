# Findings — P20 Virtual Scroll

Format: `- [ ] → Phase N: <Erkenntnis>`

- [ ] → Phase 3: „Alle auswählen" hatte bisher einen Button pro Monatsgruppe
  (`.grid__month-head`). Der ist mit den Gruppen komplett weggefallen — es gibt
  aktuell **keine** UI-Stelle mehr, die `GalerieGrid.onSelectAll()` auslöst
  (Output/Wiring funktioniert, aber niemand ruft es auf). AK „Bulk-Select
  liefert alle geladenen IDs korrekt" ist nur die Event-Kette, nicht die
  Erreichbarkeit für den User. Braucht eine neue Stelle (z.B. `sub-toolbar` bei
  aktivem `selectionMode`, oder ein schmaler Balken über `.grid__scroll-container`).
- [ ] → Phase 3: `gallerySelectors.selectGroups` (`store/gallery/gallery.selectors.ts`)
  wird nach diesem Umbau von keinem Consumer mehr referenziert — weder
  `galerie.ts` noch `favoriten.ts` nutzen `groups` mehr. Bewusst nicht in Phase 2
  angefasst (Store-Layer war nicht im Checklisten-Scope). Kandidat zum Entfernen,
  falls nichts anderes noch draufzeigt (kurz greppen vor dem Löschen).
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
