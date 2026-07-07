# Phase 4 — Text-Semantiksuche verdrahten

**Komplexität:** standard · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `backend/photofant/api/search.py` — `semantic_search` mit `query` (Text→Bild, existiert, embeddet via
  `embed_text`). **Kein Backend-Umbau nötig** — nur Frontend-Anbindung. (Der Endpoint braucht P35s
  `resolve_image_embedder()` im Text-Pfad — bereits Teil von P35.)
- `frontend/src/app/ui/search-box/` — die globale Suchbox (heute exakte Tag-/Caption-Suche, `q_mode=text`).
- `frontend/src/app/store/search/`, `store/filters/` — der Reverse-/Ähnlichkeits-Filtermodus aus Phase 1/2
  (geordnete `similar_ids`) wird für die Text-Treffer wiederverwendet.
- `backend/photofant/api/assets.py` — `list_assets(similar_ids=…)` aus Phase 1.

## Warum das fast geschenkt ist
Der Text-Pfad des `/semantic`-Endpoints ist gebaut, aber hatte nie einen Frontend-Aufrufer (toter Code).
SigLIP2s mehrsprachiger Text-Encoder (P35) macht ihn brauchbar. Die Treffer sind wieder eine geordnete
id-Liste → **derselbe** Ordered-Filter-Mechanismus wie bei der Reverse-Bildsuche.

## AK der Phase
- [ ] In der Suchbox ein klar beschrifteter Umschalter/Modus „semantische Suche" (neben der exakten
      Tag-/Caption-Suche) — mit Tooltip, was er tut („nach Bildinhalt suchen, nicht nach Tag-Text").
      Idiotensicherheit: der Unterschied exakt ↔ semantisch ist ohne Erklärung erkennbar.
- [ ] Freitext im Semantik-Modus → `POST /api/search/semantic {query}` → Ergebnis als geordneter
      `similar_ids`-Filter (Wiederverwendung Phase 1/2), Galerie zeigt die Treffer.
- [ ] 409 `SEMANTIC_SEARCH_UNAVAILABLE` (kein Embedder aktiv) zeigt eine klare deutsche Meldung.
- [ ] Chip/Anzeige macht klar, dass ein Semantik-Ergebnis aktiv ist; Zurücksetzen wie bei den anderen Filtern.
- [ ] `npm run lint` + `npm run build` grün.

## Doc-Updates
- [ ] `docs/routes.md` — Vermerk, dass der `query`-Zweig von `/api/search/semantic` jetzt einen Frontend-Aufrufer hat.
- [ ] `docs/code-map.md` — Suche-Zeile: Semantik-Modus im Frontend-Slice.

## Report-Back
