# Phase 3 — Lightbox „Ähnliche Bilder" (Related-Rail, p26-kompatibel) + „mehr"-Sprung

**Komplexität:** standard · **Status:** done

## Kontext (vor dem Bauen lesen)
- `frontend/src/app/features/galerie/lightbox/` — die Lightbox (Screen-Eigentümer P15). Hier kommt die Sektion rein.
- `frontend/src/app/store/gallery/`, `store/filters/` — Öffnen der Galerie im Reverse-Modus (aus Phase 2 wiederverwenden).
- `services/…` — Aufruf `POST /api/search/semantic` mit `like_asset_id` (existiert).
- **p26-Vorgabe (README):** die Rail ist eine **generische** Komponente, Item-Typ
  `{ assetId: number; score: number; reasons: Reason[] | null }`. P36 übergibt `reasons: null`.
- Konventionen: `docs/conventions/angular.md`.

## Entscheidung (2026-07-07, während Phase 1 gefunden, siehe FINDINGS.md)
Es existiert bereits ein „Ähnliche Bilder"-Button in der Lightbox (`lightbox.html:112-121`), der ein
Klick-Overlay öffnet (`lightbox.html:868-893`, `openSimilarOverlay()` → `GET /api/assets/{id}/similar`,
Schwellenwert-basiert, Teil der Duplikat-Erkennung — Klick auf ein Treffer-Thumbnail öffnet den
Dupe-Resolve-Dialog). **Entschieden: die neue Related-Rail ersetzt dieses Overlay komplett**, kein
Nebeneinander. Der bestehende Duplikat-Abgleich als eigener Workflow bleibt unangetastet im Review-Tab
(`/api/review/dupes`, unabhängig von der Lightbox) — nur der Lightbox-spezifische Schnellzugriff per
Klick-Overlay entfällt.

## AK der Phase
- [x] Neue, wiederverwendbare Rail-Komponente (`features/galerie/lightbox/related-rail/` o.ä.), rendert Karten aus
      `{ assetId, score, reasons }` — Vorschaubild + Ähnlichkeits-Prozent; `reasons` (wenn gesetzt) als Begründungs-
      Checkliste, sonst weggelassen. **Struktur so, dass P26 dieselbe Komponente mit gefüllten `reasons` nutzt.**
- [x] In der Lightbox unter dem Detail-Bereich zeigt die Rail bis zu `reverseSearch.similarLimit` (10) Ähnliche
      zum offenen Bild (`like_asset_id`); Klick auf eine Karte öffnet dieses Bild in der Lightbox.
- [x] „mehr"-Button unter der Rail öffnet die Galerie im **Reverse-Modus** (Phase 2) zu genau dem offenen Bild
      (`similar_ids` aus dem `like_asset_id`-Ergebnis; Quell-Thumbnail = das offene Bild).
- [x] Leerer/Fehlerfall (kein Embedder, keine Ähnlichen) zeigt einen dezenten Hinweis statt einer leeren Fläche.
- [x] **Altes Overlay entfernen:** `openSimilarOverlay()`/`closeSimilarOverlay()`/`showSimilarOverlay`/
      `similarAssets`/`similarLoading`/`openSimilarCompare()`/`onSimilarResolve()`/`selectedSimilarPair` +
      das `similar-scrim`/`similar-overlay`-Markup (`lightbox.html:868-909`) und den alten „Ähnliche Bilder"-
      Button (`lightbox.html:112-121`) aus `lightbox.ts`/`lightbox.html` entfernen — die neue Rail übernimmt
      den Slot. `AssetService.getSimilarAssets()` (`asset.service.ts:143`) + `SimilarAsset`-Modell nur entfernen,
      falls wirklich kein anderer Aufrufer mehr existiert (kurz grep'en, `DupeCompare` hängt evtl. noch dran).
- [x] `npm run lint` + `npm run build` grün.

## Doc-Updates
- [x] `docs/code-map.md` — Galerie/Lightbox-Zeile um die Related-Rail ergänzen (Hinweis: von P26 mitbenutzt).
- [ ] STATE.md/Archiv: Plan nach `docs/archive/2026-07/` verschieben, STATE auf nächsten Plan/`(kein aktiver Plan)` —
      erst nach Phase 4 (Text-Semantiksuche), P36 ist noch nicht komplett.

## Report-Back
- **Abweichung vom AK:** `AssetService.getSimilarAssets()` + `SimilarAsset`-Modell entfernt (kein anderer Frontend-
  Aufrufer mehr, `DupeCompare` hing nicht daran — nutzt `DupePair`/`AssetSummary`). Backend-Endpoint
  `GET /api/assets/{id}/similar` bleibt bestehen, wird noch von `mcp/tools/library.py` aufgerufen.
- **Nicht in dieser Phase entfernt (🟡 Follow-up, nicht blockierend):** `AssetService.setAssetOriginal()`
  (`asset.service.ts`) war ausschließlich vom jetzt entfernten `onSimilarResolve()` aufgerufen — nach dieser
  Phase ohne Frontend-Caller. Ebenso der Backend-Endpoint `PATCH /assets/{id}/original` (kein MCP-Aufrufer).
  Nicht Teil des AK, daher stehen gelassen statt eigenmächtig mitentfernt — bei Bedarf eigener kleiner Cleanup.
- „mehr"-Sprung ruft `semanticByAsset()` ohne explizites `limit` auf (Server-Default 24 aus
  `SemanticSearchRequest.limit`) statt der Rail-Limit (10) — bewusst, damit die Reverse-Galerie mehr zeigt als
  die Rail-Vorschau.
