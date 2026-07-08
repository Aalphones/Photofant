# Phase 1 — Backend: Upload-Embed-Endpoint + Galerie-`similar_ids`

**Komplexität:** standard · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `backend/photofant/api/search.py` — `semantic_search` (Muster: over-fetch mit `_CANDIDATE_FACTOR`,
  soft-deleted-Filter via `_active_asset_ids`, 409-Fehlerbilder). Vorlage für den neuen Endpoint.
- `backend/photofant/inference/image_embedder.py` (aus P35) — `resolve_image_embedder()`.
- `backend/photofant/db/vector_index.py` — `search(session, query_embedding, limit)`.
- `backend/photofant/api/assets.py` — `list_assets` + `q_mode`-Zweige (hier kommt `similar_ids` dazu).
- `backend/photofant/settings.py` — neue Keys `reverseSearch.*` registrieren (Muster: bestehende Keys + Typ-Map + Defaults).

## AK der Phase
- [x] `POST /api/search/by-image` (multipart, Feld `file`, optional `limit`): dekodiert das Bild (PIL, `convert("RGB")`),
      `resolve_image_embedder().embed()`, `vector_index.search()`, filtert soft-deleted (wie `semantic_search`).
      Response `{ hits: [{asset_id, score}] }`. 409 `SEMANTIC_SEARCH_UNAVAILABLE` ohne aktiven Embedder.
      Upload wird **nicht** gespeichert/importiert.
- [x] Upload-Guards: `Content-Type`/Bild-Dekodierbarkeit prüfen (kein Bild → 422 klare Meldung), Größe gegen
      `reverseSearch.maxUploadBytes` (zu groß → 413/422 klare Meldung).
- [x] `list_assets` akzeptiert `similar_ids` (geordnete id-Liste) → liefert genau diese aktiven Assets **in der
      übergebenen Reihenfolge** (z.B. `ORDER BY CASE id …` oder Nachsortierung in Python), respektiert bestehende
      Sichtbarkeits-Filter (soft-delete).
- [x] `reverseSearch.similarLimit` (10), `reverseSearch.maxUploadBytes`, `reverseSearch.minScore` (0.0) in `settings.py`.
- [x] `ruff check .` grün; Test für `by-image` (aktiver Embedder gemockt → hits; kein Embedder → 409; kaputter Upload → 422).

## Doc-Updates
- [x] `docs/routes.md` — `POST /api/search/by-image` + `list_assets`-Parameter `similar_ids`.
- [x] `docs/code-map.md` — Suche-Zeile um den by-image-Pfad ergänzen.

## Report-Back
`POST /api/search/by-image` + `similar_ids`-Filter auf `GET /api/assets` stehen, settings.json hat die
`reverse_search`-Gruppe. 13 neue Tests grün (`test_search_by_image.py` + 4 Ergänzungen in
`test_assets_search.py`), `ruff check` sauber auf allen angefassten Dateien. Voller Backend-Testlauf zeigt
13 vorbestehende Fehler (comfyui/caption_config) — verifiziert per `git stash`, existieren identisch auf
`master`, nicht durch diese Phase verursacht.

🟡 **Fund während der Umsetzung (nicht Teil dieser Phase, siehe FINDINGS.md):** Die Lightbox hat bereits
eine „Ähnliche Bilder"-Funktion (`/api/assets/{id}/similar`, Schwellenwert-basiert, Teil der
Duplikaterkennung). P36 Phase 3 plant dort eine zweite, Top-10-basierte Related-Rail — vor Phase 3 klären,
ob konsolidiert oder beides parallel mit klarer Beschriftung bleibt.
