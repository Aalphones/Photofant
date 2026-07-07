# STATE

**Aktiver Plan:** `docs/planning/2026-07-07_p35-siglip2-swap/`
**Phase:** 2/3 — Vektor-Dimension-Migration (768 → 1024) (pending)
**Nächster Schritt:** Phase 2 starten — `vector_index.EMBEDDING_DIM` auf 1024, `vec0`-Tabelle
migrieren, Übergangs-Invariante (alle `clip_embedding` NULL + `embedding_done=False`) herstellen.
Phase-2-Datei + FINDINGS (Phase-2-Tag zum Dim-Guard) lesen. **Modell für Phase 2: `opusplan`**
(heikel — Migration + Übergangs-Invariante).

_Phase 1 (Austausch-Naht + SigLIP2-Adapter + Manifest) ✅ complete, committet. Naht steht,
alle 5 Konsumenten model-agnostisch, ADR-021/022 + code-map aktualisiert. Offen für User-Smoke:
SigLIP2-Preprocessing/Text gegen echte Config-Dateien verifizieren (Modell erst herunterladen)._

**Backlog danach (User-Reihenfolge, 2026-07-07):** `2026-07-07_p36-reverse-image-search` →
`2026-07-07_p37-dinov2-reranking` → `2026-07-01_p22-knowledge-engine` bis `p26-recommendation-engine`
(in Nummernreihenfolge) → `2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`.

_MCP-Schnittstelle (`2026-07-06_mcp-schnittstelle`) fertig und archiviert nach
`docs/archive/2026-07/2026-07-06_mcp-schnittstelle/` — 63 Tools über 6 Phasen, Confirmation-Gate
auf alle destruktiven Aktionen. Offener Follow-up (nicht blockierend): Live-MCP-Handshake gegen
`/mcp` (MCP Inspector / Claude Desktop) noch nicht durch den User geprüft — siehe Archiv-README
„Follow-ups"._
