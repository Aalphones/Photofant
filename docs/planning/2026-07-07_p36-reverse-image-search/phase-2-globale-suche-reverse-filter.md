# Phase 2 — Globale Suche: Drag & Drop / Upload → Reverse-Filter

**Komplexität:** heikel (UI-Fluss + neuer exklusiver Filter-Modus) · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `frontend/src/app/ui/search-box/` — die globale Suchbox (hier kommt die Drop-Zone/Upload-Affordance dazu).
- `frontend/src/app/store/filters/` + `store/search/` — Filter-/Such-Zustand (neuer Reverse-Modus).
- `frontend/src/app/features/galerie/` (grid, filter-rail, sub-toolbar) — wo Filter-Chips/Ergebnisse erscheinen.
- `frontend/src/app/services/…` — HTTP-Service für Suche (Aufruf `POST /api/search/by-image`).
- Konventionen: `docs/conventions/angular.md`, `docs/conventions/ngrx.md`.
- **Design-Lage (README):** vor Bau `docs/design/` auf ein Such-Mockup prüfen.

## AK der Phase
- [ ] In/an der globalen Suchbox eine **erkennbare** Drop-Zone + Upload-Button (Bild-Icon) mit Tooltip
      („Bild ablegen oder wählen, um ähnliche zu finden") — Idiotensicherheit: ohne Erklärung bedienbar.
- [ ] Drop **oder** Upload → `by-image` aufrufen → Reverse-Modus im `store/filters/` setzen: hält Quell-Thumbnail
      (Data-URL des Uploads) + geordnete `similar_ids`; Galerie lädt via `list_assets(similar_ids=…)`.
- [ ] Reverse-Modus ist **exklusiv**: aktiviert er, treten Text-/Tag-/Facetten-Filter zurück (sauberer, dokumentierter
      Übergang); ein entfernbarer Chip „Ähnliche zu [Vorschau] ✕" setzt zurück und stellt den Normalzustand her.
- [ ] Fehlerfälle (kein Embedder / zu groß / kein Bild) zeigen die deutsche Backend-Meldung als Toast/Banner.
- [ ] `npm run lint` + `npm run build` grün.

## Doc-Updates
- [ ] `docs/code-map.md` — Suche-Zeile: Reverse-Filter-Modus im Frontend-Slice vermerken.

## Report-Back
