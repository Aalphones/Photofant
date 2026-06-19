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

- [ ] `DupePair`-Typ in `frontend/src/app/features/review/` definieren
- [ ] Review-Feature-State erweitern: `dupePairs: DupePair[]`, `dupesLoading: boolean`
- [ ] Actions: `loadDupePairs`, `loadDupePairsSuccess`, `resolveDupePair`, `resolveDupePairSuccess`, `triggerDupeScan`
- [ ] Effect: `loadDupePairs` → `GET /api/review/dupes`; `resolveDupePair` → `PATCH …`; `triggerDupeScan` → `POST /api/jobs/dupe-scan`
- [ ] Selector: `selectPendingDupePairs`, `selectDupePairsCount`

### Komponenten (ng generate)

- [ ] `pf-review` — Hauptkomponente: Tab-Switcher + Router zu den beiden Tab-Inhalten
- [ ] `pf-review-dupes` — Duplikate-Tab: Liste + Header + leerer Zustand
- [ ] `pf-dupe-pair-row` — einzelne Zeile in der Liste
- [ ] `pf-dupe-compare` — Compare-Modal (ggf. als `pf-dupe-compare-dialog`)

### CSS (BEM)

- Block `review-dupes`, `dupe-pair`, `dupe-compare` — kein `rq-`-Prefix aus dem Design übernehmen, Angular-BEM-Konvention nutzen

### Docs

- [ ] `docs/conventions/angular.md` — falls neue Pattern (Tab-Switcher, Review-Modal) dokumentieren

## Report-Back
