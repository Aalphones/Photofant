# Phase 3 — Frontend: Review-Dupes nachladen

## Kontext (vor Umsetzung lesen)

- `README.md` dieses Plans — Kontrakt-Sektion
- `frontend/src/app/store/review/` — actions, reducer, effects, selectors (EntityAdapter)
- `frontend/src/app/services/review.service.ts` — API-Aufruf `loadDupePairs`
- `frontend/src/app/features/review/review-dupes/` — Komponente + Template
- Konventionen: `docs/conventions/angular.md`, `docs/conventions/ngrx.md`

## Abnahmekriterien

1. Initialer Load holt Seite 1 (`offset=0, limit=DUPE_PAGE_SIZE=50`); DOM enthält max. 50
   Paar-Zeilen.
2. „Mehr laden"-Button unter der Liste: sichtbar solange `geladen < total`, disabled während
   des Nachladens (Spinner/Label „Lädt…"), hängt die nächste Seite an Bestehendes an.
3. Kopfzeile zeigt „<geladen> von <total>" statt nur der geladenen Anzahl.
4. Paar auflösen: Zeile verschwindet (wie heute), `total` sinkt lokal um 1 — kein Full-Reload.
5. Neuer Scan getriggert / Seite neu betreten: Liste resettet auf Seite 1.
6. `npm run lint` + `npm run build` grün.

## Checkliste

- [ ] `review.service.ts`: `loadDupePairs(offset, limit)` → `{ items, total }` (Typ in
      `models/review.model.ts` ergänzen)
- [ ] `store/review`: State um `total` + `offset` + `isLoadingMore` erweitern;
      Actions `loadDupePairs` (reset) / `loadMoreDupePairs` (append); Reducer `addMany`
      statt `setAll` beim Append; `resolveDupePairSuccess` dekrementiert `total`
- [ ] Selector `selectTotal` (Backend-Total, nicht Entity-Count) + `selectHasMore`
- [ ] `review-dupes.ts/html`: „Mehr laden"-Button, „X von Y"-Kopfzeile, Loading-State
- [ ] `DUPE_PAGE_SIZE = 50` als benannte Konstante (kein Magic Number im Effect)
- [ ] Doc-Update: `docs/routes.md` bereits in Phase 2 erledigt — prüfen, sonst nichts
- [ ] `npm run lint` + `npm run build`

## Report-Back
