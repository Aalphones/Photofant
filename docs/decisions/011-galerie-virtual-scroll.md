# ADR-011 — Virtual-Scroll-Strategie: @tanstack/angular-virtual, Row-level

## Kontext
Die Galerie rendert alle Assets als gescrollte Flex-Rows ohne Virtualisierung.
Bei 6000+ Assets pro Monat entstehen tausende DOM-Knoten — messbare Performance-Probleme.

## Betrachtete Optionen
1. **Angular CDK VirtualScrollViewport** — für uniforme Item-Höhen ausgelegt,
   aber Items haben uniforme Zeilenhöhe, nicht uniforme Breite. Das Justified-Grid-
   Layout (variable Breiten innerhalb einer Zeile) ist nicht abbildbar.

2. **Custom Group-level** — IntersectionObserver pro Monatsgruppe, Placeholder-Div.
   Zu grob: eine Gruppe mit 6000 Bildern rendert alles auf einmal wenn sichtbar.

3. **@tanstack/angular-virtual, Row-level** — virtualisiert auf Zeilen-Ebene.
   Braucht unsere eigene Row-Breaking-Engine (computeRows), übernimmt aber
   Scroll-Position-Tracking, Total-Height-Spacer und Overscan.

## Entscheidung
Option 3. Row-level Virtualisierung passt zur Datenform (flache Asset-Liste,
uniforme Zeilenhöhe = baseHeight). @tanstack/virtual ist stabil und battle-tested.
Die Row-Breaking-Engine ist ~40 Zeilen purer Code ohne Framework-Abhängigkeit.

## Konsequenzen
- Monatsgruppen-Header entfallen (kein `selectGroups` mehr im Grid). Die Selektoren
  `selectGroups`/`buildGroups` (`gallery.selectors.ts`) hatten nach dem Umbau keinen
  Consumer mehr und wurden in Phase 3 entfernt.
- Row-Breaking-Algorithmus kann ±1 Zeile von Browser-Flexbox abweichen
  (Sub-Pixel-Rounding) — führt zu ±ROW_HEIGHT px Drift in der Scroll-Gesamthöhe.
- Scroll-Container muss ein explizites Element mit overflow-y: auto sein
  (kein Window-Scroll). Galerie-Layout entsprechend angepasst.
- `GRID_PADDING` und `GRID_GAP` in row-layout.ts sind CSS-Konstanten —
  Styling-Änderungen an grid.scss müssen dort nachgezogen werden.
- **„Gruppierung"-Button entfernt:** Der Sort/Group-Umschalter in der Sub-Toolbar
  (`cycleGroup()`) änderte nach dem Wegfall der Gruppen-Header nur noch
  unsichtbaren Store-Status (`filtersFeature.selectGroup`) und löste einen
  wirkungslosen Refetch aus — vorgetäuschte Funktion. In Phase 3 komplett
  kaskadiert entfernt: Button/State in `sub-toolbar.ts`/`.html`,
  `filtersActions.setGroup`, `FiltersState.group`, `filtersSelectors.group`,
  der `setGroup`-Eintrag im `onFiltersChange$`-Effect, sowie die Typen
  `GroupKey`/`GROUP_KEYS` und das nie konsumierte `AssetGroup` (Modelltyp für
  die alte gruppierte Ansicht) aus `models/asset.model.ts`.
