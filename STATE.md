# STATE

**Aktiver Plan:** `docs/planning/2026-07-07_p36-reverse-image-search/` — Phase 3 (Lightbox „Ähnliche Bilder" als
p26-kompatible Related-Rail + „mehr"-Sprung, ersetzt das alte Similar-Overlay komplett) **fertig**, lint+build
grün. Nächster Schritt: Phase 4 (toter `POST /api/search/semantic`-Text-Pfad → Frontend verdrahten). Danach
Plan komplett → archivieren, STATE auf nächsten Plan setzen.

**Follow-up aus Phase 3 (🟡 nicht blockierend):** `AssetService.setAssetOriginal()` + Backend-Endpoint
`PATCH /assets/{id}/original` sind seit der Overlay-Entfernung ohne Aufrufer (weder Frontend noch MCP) —
bewusst nicht mitentfernt (außerhalb des Phase-3-AK), bei Gelegenheit eigener kleiner Cleanup. Details:
`phase-3-lightbox-aehnliche.md` Report-Back.

**Backlog danach (User-Reihenfolge, 2026-07-07):** `2026-07-07_p37-dinov2-reranking` →
`2026-07-01_p22-knowledge-engine` bis `p26-recommendation-engine` (in Nummernreihenfolge) →
`2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`.

---

_P35 (Bild-Embedder swappbar + CLIP → SigLIP2) ✅ komplett, archiviert nach
`docs/archive/2026-07/2026-07-07_p35-siglip2-swap/`. Alle 702 Assets auf SigLIP2 (1024-dim) umgestellt,
`dupe_clip_threshold` nach realer Kalibrierung bei 0.03 belassen (keine saubere Trennlinie zwischen
echten Duplikaten und Fremdpaaren im Band 0.025–0.030 unter SigLIP2 — Details ADR-021). Unterwegs zwei
echte Bugs gefunden + gefixt: fehlender Re-Embed-Button (jetzt in der Wartung-Seite) und ein
Exklusivitäts-Bug, der kurzzeitig beide Bild-Embedder gleichzeitig aktiv sein ließ und die Textsuche
mit einem Dimension-Mismatch abgeschossen hat (Resolver jetzt selbstheilend, `inference/image_embedder.py`).
Follow-up (nicht blockierend): `training_near_dupe_clip_threshold` nicht separat kalibriert (kein aktives
Trainingsset) — bei nächster Trainingsset-Erstellung nachziehen. Alle Details im Archiv-README._

_MCP-Schnittstelle (`2026-07-06_mcp-schnittstelle`) fertig und archiviert nach
`docs/archive/2026-07/2026-07-06_mcp-schnittstelle/` — 63 Tools über 6 Phasen, Confirmation-Gate
auf alle destruktiven Aktionen. Offener Follow-up (nicht blockierend): Live-MCP-Handshake gegen
`/mcp` (MCP Inspector / Claude Desktop) noch nicht durch den User geprüft — siehe Archiv-README
„Follow-ups"._
