# Phase 3 — Lightbox „Ähnliche Bilder" (Related-Rail, p26-kompatibel) + „mehr"-Sprung

**Komplexität:** standard · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `frontend/src/app/features/galerie/lightbox/` — die Lightbox (Screen-Eigentümer P15). Hier kommt die Sektion rein.
- `frontend/src/app/store/gallery/`, `store/filters/` — Öffnen der Galerie im Reverse-Modus (aus Phase 2 wiederverwenden).
- `services/…` — Aufruf `POST /api/search/semantic` mit `like_asset_id` (existiert).
- **p26-Vorgabe (README):** die Rail ist eine **generische** Komponente, Item-Typ
  `{ assetId: number; score: number; reasons: Reason[] | null }`. P36 übergibt `reasons: null`.
- Konventionen: `docs/conventions/angular.md`.

## AK der Phase
- [ ] Neue, wiederverwendbare Rail-Komponente (`features/galerie/lightbox/related-rail/` o.ä.), rendert Karten aus
      `{ assetId, score, reasons }` — Vorschaubild + Ähnlichkeits-Prozent; `reasons` (wenn gesetzt) als Begründungs-
      Checkliste, sonst weggelassen. **Struktur so, dass P26 dieselbe Komponente mit gefüllten `reasons` nutzt.**
- [ ] In der Lightbox unter dem Detail-Bereich zeigt die Rail bis zu `reverseSearch.similarLimit` (10) Ähnliche
      zum offenen Bild (`like_asset_id`); Klick auf eine Karte öffnet dieses Bild in der Lightbox.
- [ ] „mehr"-Button unter der Rail öffnet die Galerie im **Reverse-Modus** (Phase 2) zu genau dem offenen Bild
      (`similar_ids` aus dem `like_asset_id`-Ergebnis; Quell-Thumbnail = das offene Bild).
- [ ] Leerer/Fehlerfall (kein Embedder, keine Ähnlichen) zeigt einen dezenten Hinweis statt einer leeren Fläche.
- [ ] `npm run lint` + `npm run build` grün.

## Doc-Updates
- [ ] `docs/code-map.md` — Galerie/Lightbox-Zeile um die Related-Rail ergänzen (Hinweis: von P26 mitbenutzt).
- [ ] STATE.md/Archiv: Plan nach `docs/archive/2026-07/` verschieben, STATE auf nächsten Plan/`(kein aktiver Plan)`.

## Report-Back
