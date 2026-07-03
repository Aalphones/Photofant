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

- [x] `review.service.ts`: `loadDupePairs(offset, limit)` → `{ items, total }` (Typ in
      `models/review.model.ts` ergänzen)
- [x] `store/review`: State um `total` + `offset` + `isLoadingMore` erweitern;
      Actions `loadDupePairs` (reset) / `loadMoreDupePairs` (append); Reducer `addMany`
      statt `setAll` beim Append; `resolveDupePairSuccess` dekrementiert `total`
- [x] Selector `selectTotal` (Backend-Total, nicht Entity-Count) + `selectHasMore`
- [x] `review-dupes.ts/html`: „Mehr laden"-Button, „X von Y"-Kopfzeile, Loading-State
- [x] `DUPE_PAGE_SIZE = 50` als benannte Konstante (kein Magic Number im Effect)
- [x] Doc-Update: `docs/routes.md` bereits in Phase 2 erledigt — prüfen, sonst nichts
- [x] `npm run lint` + `npm run build`

## Report-Back

- Wegen der Namenskollision zwischen NgRx-EntityAdapter (`selectTotal` = geladene Anzahl)
  und dem Backend-Total wurde **derselbe Kniff wie bei `gallerySelectors`** übernommen:
  neuer `selectServerTotal` (liest `state.total` direkt), `selectTotal` bleibt die
  geladene Entity-Anzahl. `selectHasMore = total > loaded`.
- `state.offset` ist der Fetch-Cursor für „Mehr laden" (Anzahl bereits geladener Items),
  unabhängig von der Entity-Anzahl nach Auflösen — bewusst so, sonst würde ein Resolve
  mitten in der Liste den nächsten Fetch verschieben.
- **Nachbarstelle mitgefixt:** `nav-rail.ts` bezog den Review-Badge-Count bisher aus
  `selectTotal` — vor der Pagination war das identisch mit dem Backend-Total (alles wurde
  geladen), jetzt wäre es auf `DUPE_PAGE_SIZE` gedeckelt gewesen. Auf `selectServerTotal`
  umgestellt, sonst hätte der Badge bei >50 offenen Paaren falsch niedrig anzeigt.
- AK5 „Neuer Scan getriggert … resettet auf Seite 1": es gibt keinen SSE-Hook, der die
  Liste nach Job-Abschluss automatisch neu lädt (weder vorher noch jetzt) — die Reset-
  Garantie gilt für jeden `loadDupePairs()`-Dispatch (Seiten-Eintritt). Kein Scope-Zuwachs
  für diese Phase, da nicht in der Checkliste; als Beobachtung hier vermerkt.
- `npm run lint` (`tsc --noEmit`) und `npm run build` beide grün; Bundle-Budget-Warnungen
  sind vorbestehend (Lightbox-SCSS, Initial-Bundle) und unabhängig von dieser Änderung.
