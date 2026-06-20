# Phase 5 — Frontend: Review-Tab Duplikate

## Design-Referenz

- **Pair-Liste + Compare-Modal:** `docs/design/js/dupecheck.jsx` — verbindlich als Referenz-Design; wird als eingebetteter Tab-Content umgesetzt (kein Overlay mehr, da wir im Review-Tab-Kontext sind)
- **Tab-Navigation Review:** kein eigenes Mockup → Entscheidung hier: einfacher Tab-Switcher ("Gesichter | Duplikate") am oberen Rand des Review-Containers; folgt dem bestehenden Tab-Muster der App (falls vorhanden) oder wird minimal nach Design-System eingeführt
- **Gesichter-Tab:** bleibt wie bisher (`review.jsx`-Design), unverändert

## Kontext (vor Implementierung lesen)

- `docs/planning/2026-06-19_duplikaterkennung/README.md` — Kontrakt: DupePair-Typ, API
- `docs/design/js/dupecheck.jsx` — vollständige Design-Referenz für Pair-Layout
- `docs/design/js/review.jsx` — bestehender Review-Tab (Gesichter), nicht anfassen
- `frontend/src/app/features/review/review.ts` — aktuell Placeholder, wird jetzt gebaut
- `frontend/src/app/` — NgRx Store-Muster, bestehende Services
- `docs/conventions/angular.md` + `docs/conventions/ngrx.md`

## Akzeptanzkriterien

1. Review-Tab zeigt einen Tab-Switcher: **"Gesichter"** (Platzhalter, später P7) | **"Duplikate"** — Duplikate ist der aktive Default bis P7 implementiert ist.
2. **Duplikate-Tab Layout** (nach dupecheck.jsx):
   - Header: Badge mit Anzahl offener Paare + Scan-Button ("Bibliothek durchsuchen")
   - Liste der Paare: zwei Thumbnails nebeneinander, Ähnlichkeits-Balken (Hamming-Distanz → 0% nah, 100% weit → visuell invertiert: 0 Distanz = 100% Ähnlichkeit), IDs + Dimensionen
   - Pro Paar: 4 Aktions-Buttons (A=Original, B=Original, A löschen, B löschen) + "Beide behalten"-Link
3. **Compare-Modal:** Klick auf Paar öffnet Side-by-Side-Overlay mit Vollbild beider Assets; Label "Original"/"Edit" wenn `original_id` bereits gesetzt; 4 Aktionen als Buttons im Modal-Footer.
4. Aktion löst `PATCH /api/review/dupes/{id}` aus; Paar verschwindet nach Erfolg aus Liste (optimistisches Update oder State-Reload).
5. Scan-Button triggert `POST /api/jobs/dupe-scan` (scope=all); zeigt Toast "Scan gestartet — Job läuft im Hintergrund".
6. Leere Liste: Illustration + Text "Keine Duplikate in der Queue" + Hinweis "Scan starten um bestehende Bibliothek zu prüfen".
7. Review-Queue-Badge in Nav-Rail zeigt Gesamtzahl offener Duplikat-Items.

## Checkliste

### NgRx / State

- [x] `DupePair`-Typ in `frontend/src/app/models/review.model.ts` definiert (+ `AssetSummary`, `DupeResolution`)
- [x] Review-Feature-State: `EntityState<DupePair>`, `isLoading`, `error` — via `createEntityAdapter`
- [x] Actions: `loadDupePairs`, `loadDupePairsSuccess/Failure`, `resolveDupePair`, `resolveDupePairSuccess/Failure`, `triggerDupeScan`, `triggerDupeScanSuccess/Failure`
- [x] Effects: load → `GET /api/review/dupes`; resolve → `PATCH`; scan → `POST /api/jobs/dupe-scan`; Init-Effect → lädt Paare beim App-Start (Badge)
- [x] Selectors: `selectAll`, `selectTotal`, `selectIsLoading`, `selectError`

### Komponenten (ng generate)

- [x] `pf-review` — Shell: Tab-Switcher (Gesichter | Duplikate), Duplikate als Default
- [x] `pf-review-dupes` — Duplikate-Tab: Header mit Badge + Scan-Button, Liste, leerer Zustand, Lade-Zustand
- [x] `pf-dupe-pair-row` — Zeile: zwei Thumbnails, Similarity-Bar, IDs, 4 Action-Buttons
- [x] `pf-dupe-compare` — Compare-Modal: Side-by-Side, 5 Resolve-Aktionen im Footer

### CSS (BEM)

- [x] Blöcke `review-dupes`, `dupe-pair`, `dupe-compare` — BEM-Konvention, keine `rq-`/`dc-`-Prefixe aus dem Design

### Registrierung

- [x] `reviewFeature` + `ReviewEffects` in `app.config.ts`
- [x] Barrel-Einträge: `store/review/index.ts` → `store/index.ts`; `ReviewService` → `services/index.ts`; Models → `models/index.ts`
- [x] Icons `compare` + `link` zur `Icon`-Komponente hinzugefügt
- [x] Nav-Rail: `toolItems` zu computed Signal, Review-Badge zeigt `reviewSelectors.selectTotal`

### Docs

- [x] Kein neues Pattern nötig — Tab-Switcher folgt dem Einstellungen-Shell-Muster

## Report-Back

Phase 5 complete (2026-06-20). Alle AK erfüllt:
- Review-Tab mit Tab-Switcher (Gesichter-Placeholder | Duplikate-Default)
- Duplikate-Liste mit Score-Bar, Thumbnails, 4+1 Aktionen pro Paar
- Compare-Modal Side-by-Side mit 5 Resolve-Buttons
- Scan-Button triggert `POST /api/jobs/dupe-scan`
- Empty-State + Loading-State
- Nav-Rail-Badge zeigt offene Duplikat-Paare (Init-Effect)
