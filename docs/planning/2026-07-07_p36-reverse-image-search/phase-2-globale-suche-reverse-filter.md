# Phase 2 — Globale Suche: Drag & Drop / Upload → Reverse-Filter

**Komplexität:** heikel (UI-Fluss + neuer exklusiver Filter-Modus) · **Status:** done

## Kontext (vor dem Bauen lesen)
- `frontend/src/app/ui/search-box/` — die globale Suchbox (hier kommt die Drop-Zone/Upload-Affordance dazu).
- `frontend/src/app/store/filters/` + `store/search/` — Filter-/Such-Zustand (neuer Reverse-Modus).
- `frontend/src/app/features/galerie/` (grid, filter-rail, sub-toolbar) — wo Filter-Chips/Ergebnisse erscheinen.
- `frontend/src/app/services/…` — HTTP-Service für Suche (Aufruf `POST /api/search/by-image`).
- Konventionen: `docs/conventions/angular.md`, `docs/conventions/ngrx.md`.
- **Design-Lage (README):** vor Bau `docs/design/` auf ein Such-Mockup prüfen.

## AK der Phase
- [x] In/an der globalen Suchbox eine **erkennbare** Drop-Zone + Upload-Button (Bild-Icon) mit Tooltip
      („Bild ablegen oder wählen, um ähnliche zu finden") — Idiotensicherheit: ohne Erklärung bedienbar.
- [x] Drop **oder** Upload → `by-image` aufrufen → Reverse-Modus im `store/filters/` setzen: hält Quell-Thumbnail
      (Data-URL des Uploads) + geordnete `similar_ids`; Galerie lädt via `list_assets(similar_ids=…)`.
- [x] Reverse-Modus ist **exklusiv**: aktiviert er, treten Text-/Tag-/Facetten-Filter zurück (sauberer, dokumentierter
      Übergang); ein entfernbarer Chip „Ähnliche zu [Vorschau] ✕" setzt zurück und stellt den Normalzustand her.
- [x] Fehlerfälle (kein Embedder / zu groß / kein Bild) zeigen die deutsche Backend-Meldung als Toast/Banner.
- [x] `npm run lint` + `npm run build` grün.

## Doc-Updates
- [x] `docs/code-map.md` — Suche-Zeile: Reverse-Filter-Modus im Frontend-Slice vermerken.

## Report-Back

**Gebaut:**
- Suchbox (`ui/search-box/`): Drop-Zone (gestrichelter Akzent-Rand + „Bild ablegen → Ähnliche finden"-Overlay)
  + Bild-Button (`scan`-Icon, Tooltip). Drop **oder** Klick → `SearchService.searchByImage` → `by-image`.
- Neuer `SearchService` (`services/search.service.ts`) + Such-Modelle (`models/search.model.ts`:
  `SearchHit`/`SemanticSearchResponse`/`ReverseSearchState`).
- Exklusiver Reverse-Modus im `store/filters/` (`reverseSearch: ReverseSearchState | null`): setzen räumt
  Inhalts-Filter weg + zwingt `mediaType='photos'` + leert die Textsuche (search-Reducer hört mit); jeder echte
  Filter **und** jede neue Text-/Semantiksuche beenden ihn wieder (Reducer-Exklusivität, beidseitig).
- Galerie: `selectFetchParams` trägt `similarIds`, der Effect sendet `similar_ids` **statt** `q`; Chip in der
  sub-toolbar (`kind: 'reverse'`, Vorschau-Avatar) entfernt den Modus.
- **Kollisions-Fix:** `shell.onDrop` überspringt den Import-Dialog, wenn das Drop-Ziel in der Suchbox liegt
  (globaler Import-Drop und Reverse-Drop koexistieren jetzt sauber).

**Abweichungen / Entscheidungen (freihändig, kein Mockup — wie im README-Kontrakt freigegeben):**
- Quell-Vorschau wird auf ein 96px-JPEG-Thumbnail (Canvas) heruntergerechnet statt die volle Upload-Data-URL
  (bis 15 MB) in den Store zu legen.
- Leere Trefferliste → **kein** Reverse-Modus (Toast „Keine ähnlichen Bilder gefunden."), weil `similar_ids=[]`
  im Backend sonst als „kein Filter" durchfällt und die ganze Galerie zeigt.
- Upload-Größe wird nicht clientseitig geprüft — das Backend liefert die deutsche 413-Meldung, die als Toast erscheint.
