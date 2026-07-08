# STATE

**Aktiver Plan:** `docs/planning/2026-07-07_p37-dinov2-reranking/`
**Phase:** 4/4 — Dupe-Scan auf DINOv2 + Schwellwert-Rekalibrierung (pending)
**Nächster Schritt:** Phase 4 starten — `embedding_job._check_for_dupes` von SigLIP2 (`vector_index.search` +
`dupe_clip_threshold`) auf DINOv2 (`vec_asset_dino` + neuer `dupe_dino_threshold`) umstellen; alter
`dupe_clip_threshold` bleibt inert für Rollback. Kontext in `phase-4-dupe-scan.md` + FINDINGS-Eintrag → Phase 4
(`delete_dino_embedding` ist schon im Purge-Pfad verdrahtet). Komplexität: standard → `sonnet` reicht.

_Phase 3 abgeschlossen (2026-07-08): DINOv2-Rerank in beide Bild→Bild-Pfade verdrahtet, 15 Tests grün._

---

_Reihenfolge nach diesem Plan (User-Vorgabe 2026-07-07):_ `p22-knowledge-engine` … `p26-recommendation-engine`
_(Nummernreihenfolge) → `2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`._

**Offen aus P36 (nicht blockierend):** Text-Semantiksuche-Umschalter smoke-testen — Checkliste in
`docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`.

**Follow-ups aus P36 (🟡):** `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` ohne Aufrufer;
`POST /api/search/semantic`s `query`-Zweig ist totes Backend-Duplikat.
