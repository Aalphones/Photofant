# Phase 5 — Galerie-Filter, Lightbox, globale Suche (Frontend)

**Tier:** standard (bestehende Muster erweitern)

## Kontext (vor Start lesen)

- [`frontend/src/app/features/galerie/filter-rail/filter-rail.ts`](../../../frontend/src/app/features/galerie/filter-rail/filter-rail.ts) + `.html` — **das `framing`-Akkordeon ist die Vorlage** (Facet-Counts, Toggle, Label-Map, `openFraming`-Signal).
- [`frontend/src/app/store/filters/`](../../../frontend/src/app/store/filters/) — `filters.reducer.ts`/`.actions.ts`/`.selectors.ts`: wie `framings: string[]` durchläuft (Action, Reducer, `clearAllFilters`, Selector).
- [`frontend/src/app/store/gallery/gallery.effects.ts`](../../../frontend/src/app/store/gallery/gallery.effects.ts) — `onFiltersChange$` (Filter-Actions, die `reset` triggern) + `fetchPage$` (Params an `assetService.listAssets`).
- [`frontend/src/app/features/galerie/lightbox/lightbox.html`](../../../frontend/src/app/features/galerie/lightbox/lightbox.html) + `lightbox.ts` — Panel-Sektionen (Metadaten/Caption/Tags); neue Sektion „Klassifizierung" reiht sich hier ein.
- [`frontend/src/app/ui/search-box/search-box.ts`](../../../frontend/src/app/ui/search-box/search-box.ts) — Autocomplete (`AutocompleteItem`-Typen tag/person), `selectSuggestion`.

## Akzeptanzkriterien

### Filter-Rail
1. Je **aktiver Kategorie** (aus dem Store geladen) eine eigene Akkordeon-Gruppe
   mit ihren Labels als Toggle-Chips, jeweils mit Facet-Count — visuell und
   strukturell wie die `framing`-Gruppe.
2. Filter-State: neues Feld `classificationLabelIds: number[]` in `filters.reducer`,
   Action `setClassificationLabelIds`, Selector, in `clearAllFilters` zurückgesetzt.
3. `gallery.effects` `onFiltersChange$` reagiert auf die neue Action (löst `reset` aus);
   `fetchPage$` reicht `classification` an `assetService.listAssets` durch; der
   Service serialisiert die Label-IDs als wiederholte Query-Parameter.

### Lightbox
4. Neue Panel-Sektion „Klassifizierung" zeigt die `classifications` des Assets,
   **gruppiert nach Kategorie**, je Klasse Name + Confidence (Prozent/Balken).
   Fehlt eine Klassifizierung → Sektion entfällt oder zeigt dezenten Leerzustand.
5. `lightbox.ts` liest `asset.classifications` aus dem Asset-Detail (Phase-3-DTO).

### Globale Suche
6. Such-Autocomplete schlägt **Klassifizierungs-Labels** vor (neuer
   `AutocompleteItem`-Typ `class`); Auswahl setzt `setClassificationLabelIds`
   (analog zu Person → `setPersonId`).
7. Freitext-Suche findet Bilder über Label-Namen (Backend-Union aus Phase 3) —
   d.h. ein Tipp wie „Anime" liefert auch klassifizierte Treffer.

8. `npm run lint` + `npm run build` grün.

## Checkliste

- [x] `store/filters`: Feld + Action + Reducer-Case + `clearAllFilters` + Selector.
- [x] `gallery.effects.ts`: Action in `onFiltersChange$`; Param in `fetchPage$`.
- [x] `services/asset.service.ts` (bzw. wo `listAssets` lebt): `classification`-Param serialisieren.
- [x] `filter-rail.ts` + `.html` + `.scss`: Kategorie-Gruppen aus Store + Facets rendern, Toggle dispatchen.
- [x] `lightbox.html` + `lightbox.ts`: Sektion „Klassifizierung" (gruppiert, Confidence).
- [x] `search-box.ts` + `.html`: Label-Vorschläge + Auswahl-Handling.

## Report-Back

- Modelle (`asset.model.ts`): `ClassificationFacetItem`, `ClassificationCategoryFacet` ergänzt,
  `Facets.classifications` + `AssetDetailDto.classifications` (Typ `AssetClassification`).
- `store/filters`: `classificationLabelIds: number[]` durchgängig (Action, Reducer, Selector,
  `clearAllFilters`).
- `gallery.effects.ts`: neue Action löst `reset` aus; `fetchPage$` reicht die Label-IDs durch;
  **zusätzlich** ein `initClassificationCategories$`-Effect (`ROOT_EFFECTS_INIT`), der die
  Kategorien app-weit lädt — bisher lud sie exklusiv der Einstellungen-Tab, Filter-Rail/Lightbox/
  Suche hätten sonst eine leere Kategorie-Liste gesehen. Kein Plan-Abweichung im Kontrakt, nur
  eine notwendige Ergänzung, um den bestehenden Store nutzbar zu machen.
- `asset.service.ts`: `classificationLabelIds` als wiederholter `classification`-Query-Parameter
  (matcht das Phase-3-Backend-Kontrakt 1:1).
- `filter-rail`: eine Akkordeon-Gruppe je aktiver Kategorie (dynamische Closed-Set statt fixer
  Open-Signale, da die Kategorie-Anzahl zur Laufzeit variiert), Toggle + Facet-Count wie beim
  `framing`-Vorbild.
- `lightbox`: neue Panel-Sektion „Klassifizierung", nach Kategorie gruppiert, Balken + Prozent;
  nur im Asset-Modus (Klassifizierung lebt auf `AssetDetailDto`, nicht auf Face-Detail).
- `search-box`: neuer Autocomplete-Typ `class` (Icon „layers"), Client-seitiger Label-Abgleich
  gegen den bereits geladenen Kategorien-Store (kein neuer Endpoint nötig); Auswahl setzt
  `classificationLabelIds` auf `[labelId]`, analog zu `setPersonId`.
- `npm run lint` (tsc --noEmit) und `npm run build` grün (bestehende Bundle-Budget-Warnungen
  vorbestehend, nicht durch diese Phase verursacht).
