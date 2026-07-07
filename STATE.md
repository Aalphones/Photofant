# STATE

**Aktiver Plan:** `docs/planning/2026-07-07_p35-siglip2-swap/`
**Phase:** 3/3 — Re-Embed + Schwellwert-Rekalibrierung (in Arbeit)
**Nächster Schritt (User, in der laufenden App):**
1. „Neuverarbeitung: Embedding, alle" auslösen — 690 von 702 Assets warten noch auf 1024-dim Embedding
   (12 haben schon eins, SigLIP2 ist bereits aktiv, CLIP deaktiviert).
2. Danach „Duplikate scannen (vollständig)" auslösen, an bekannten echten Duplikaten prüfen, wo SigLIP2
   sie in der Cosine-Distanz einsortiert.
3. Mir die Werte melden, bei denen echte Dupes/Near-Dupes kippen → ich pflege `dupe_clip_threshold` /
   `training_near_dupe_clip_threshold` in `settings.py` + ADR-021 ein und archiviere den Plan.

Bereits verifiziert (2026-07-07): `alembic upgrade head` lief via `start.cmd`, DB steht auf Migration
`0032` (head). `model_registry`: `siglip2-large-patch16-384` enabled=1, `clip-vit-l-14` enabled=0.
Phase-3-Datei + FINDINGS (Phase-3-Tag: Preprocessing/Text erst gegen echte Config verifizieren) für
Detail lesen. **Modell für Phase 3: `sonnet`** (standard).

_Phase 2 (Dimension-Migration 768 → 1024) ✅ complete, committet. `EMBEDDING_DIM=1024`, Migration
`0032_siglip2_dim_1024.py` (Recreate `vec0` bei 1024 + Übergangs-Invariante in beide Richtungen),
`docs/models.md` nachgezogen, ruff/Alembic-Parse grün. Dim-Guard warnt erwartungsgemäß bis SigLIP2 aktiv.
Offen für User: `alembic upgrade head` selbst fahren (destruktiv — alle Embeddings weg, Re-Embed in Phase 3)._

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
