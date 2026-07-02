# Phase 1 — Bugfixes: hängender Modus, fehlender Redirect, fehlendes Reset

**Komplexität:** standard · **Status:** pending

## Kontext (vor dem Bauen lesen)

- `frontend/src/app/ui/search-box/search-box.ts` — komplette Komponente, insbesondere `selectSuggestion()` (Zeile 171-186) und der Konstruktor-Dispatch (Zeile 106-112).
- `frontend/src/app/store/search/search.reducer.ts` — alle vier Reducer-Cases.
- `frontend/src/app/store/search/search.actions.ts` — `setMode` existiert als Action, wird aber nirgends dispatcht (verifiziert per Grep über `frontend/src/app`).
- `frontend/src/app/store/gallery/gallery.effects.ts:54-76` — `onFiltersChange$`, die Trigger-Liste für `galleryActions.reset()`.
- `frontend/src/app/features/personen/personen.ts:37-44` — Referenz-Pattern für „Filter setzen + zur Galerie navigieren".
- `frontend/src/app/shell/top-bar/top-bar.html:8` — bestätigt: `pf-search-box` sitzt in der App-Shell (persistent über Routen hinweg, kein Neu-Mount-Problem).
- `docs/routes.md:482-508` — dokumentiert nur `POST /api/search/semantic`, nicht den tatsächlich genutzten `GET /api/assets?q_mode=semantic`-Pfad.

## Akzeptanzkriterien

- Eine Freitext-Eingabe **nach** einer zuvor gewählten Semantik-Suche läuft wieder als normale (Tag-)Suche, nicht mehr als CLIP-Embedding — verifizierbar z. B. per Netzwerk-Tab: `q_mode` im Request kippt zurück auf `tags`.
- Wählen des Semantik-Vorschlags löst zuverlässig einen Galerie-Refetch aus (aktuell fehlt das Wiring).
- Jede Such-Aktion (Tippen, Auswahl einer Suggestion), die auf einer Nicht-Galerie-Seite ausgelöst wird, navigiert automatisch zu `/galerie`. Ist der User bereits dort, findet **kein** unnötiger Navigations-Zyklus statt (Router-Navigate ist idempotent bei gleicher URL, aber explizit prüfen — kein Layout-Flackern).
- Nach Auswahl eines Semantik-Vorschlags zeigt das Eingabefeld nicht mehr den alten, unveränderten Text (aktuell wird `localQuery` bei diesem Zweig nie zurückgesetzt, anders als bei Person/Tag).

## Umsetzung

- [ ] `search.reducer.ts`: `setQuery` und `clear` setzen `mode` explizit auf `'tags'` zurück (nicht nur `q`). Das ist der Root-Cause-Fix — ohne den bleibt jede spätere Änderung in Phase 2 auf demselben Fundament instabil.
- [ ] `gallery.effects.ts` `onFiltersChange$`: `searchActions.setSemanticQuery` in die `ofType(...)`-Liste aufnehmen.
- [ ] `search-box.ts` `selectSuggestion()`, Zweig `type === 'semantic'`: `localQuery` und `queryInput$` wie in den anderen beiden Zweigen zurücksetzen.
- [ ] `search-box.ts`: `Router` injizieren; in `selectSuggestion()` (alle drei Zweige) und im bestehenden Tipp-Dispatch (Konstruktor, nach `searchActions.setQuery`) `router.navigate(['/galerie'])` aufrufen, **nur wenn** `router.url` nicht bereits mit `/galerie` beginnt (Guard gegen unnötige Navigation) — exaktes Pattern aus `personen.ts:43`.
- [ ] Doc: `docs/routes.md` — Abschnitt „Semantische Suche" um den tatsächlich genutzten `GET /api/assets?q_mode=semantic`-Pfad ergänzen (bestehende `POST /api/search/semantic`-Zeile bleibt stehen, aber als „kein Frontend-Aufrufer" markieren).

## Report-Back
