# STATE

**Aktiver Plan:** `docs/planning/2026-07-07_p37-dinov2-reranking/`
**Phase:** 2/4 — Zweiter Vektorraum + Embedding-Job + Migration (pending)
**Nächster Schritt:** Phase 2 starten — `asset.dino_embedding` (BLOB) + `vec_asset_dino` (float[768]) +
Ledger-Flag `dino_embedding_done` + Embedding-Job auf `role="visual_rerank"`. Manifest-`id` ist
`dinov2-with-registers-base` (768-dim). Kontext in `phase-2-zweiter-vektorraum.md` + FINDINGS-Einträge → Phase 2.

---

_Reihenfolge nach diesem Plan (User-Vorgabe 2026-07-07):_ `p22-knowledge-engine` … `p26-recommendation-engine`
_(Nummernreihenfolge) → `2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`._

**Offen aus P36 (nicht blockierend):** Text-Semantiksuche-Umschalter smoke-testen — Checkliste in
`docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`.

**Follow-ups aus P36 (🟡):** `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` ohne Aufrufer;
`POST /api/search/semantic`s `query`-Zweig ist totes Backend-Duplikat.
