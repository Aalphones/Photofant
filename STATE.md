# STATE

**Aktiver Plan:** `docs/planning/2026-07-07_p36-reverse-image-search/` — Phase 2 (Globale Suche: Drag & Drop /
Upload → Reverse-Filter) **fertig**. Nächster Schritt: Phase 3 (Lightbox „Ähnliche Bilder" als p26-kompatible
Related-Rail + „mehr"-Sprung in die Reverse-Search). **Vor Phase 3:** Design-Lage — es gibt **kein** Reverse-/
Lightbox-Mockup in `docs/design/` (nur der generelle Look ist verbindlich), daher freihändig nach
p26-Kartenkonzept (README-Kontrakt so freigegeben). Die Endpoint-Überschneidung mit dem alten Duplikat-Overlay
ist entschieden — Related-Rail ersetzt es komplett; Details + „mehr"-Wiederverwendung der Phase-2-Mechanik in
`phase-3-lightbox-aehnliche.md` + `FINDINGS.md`.

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
