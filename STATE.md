# STATE

**Aktiver Plan:** `docs/planning/2026-07-07_p37-dinov2-reranking/`
**Phase:** 3/4 — Two-Stage Re-Ranking in der Bild→Bild-Suche (pending)
**Nächster Schritt:** Phase 3 starten — Rerank-Funktion `rerank_by_appearance(query_dino_vec, candidate_asset_ids)`
+ Einhängen in `like_asset_id` (`api/search.py`) und `POST /api/search/by-image` (P36). Degradation bei
Text-Query / fehlendem DINOv2-Modell / `rerank.enabled=false`. Kontext in `phase-3-two-stage-reranking.md` +
FINDINGS-Einträge → Phase 3 (DINOv2-Lesepfad ist bewusst noch offen, `_search`-Kern in `vector_index.py` steht).

---

_Reihenfolge nach diesem Plan (User-Vorgabe 2026-07-07):_ `p22-knowledge-engine` … `p26-recommendation-engine`
_(Nummernreihenfolge) → `2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`._

**Offen aus P36 (nicht blockierend):** Text-Semantiksuche-Umschalter smoke-testen — Checkliste in
`docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`.

**Follow-ups aus P36 (🟡):** `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` ohne Aufrufer;
`POST /api/search/semantic`s `query`-Zweig ist totes Backend-Duplikat.
