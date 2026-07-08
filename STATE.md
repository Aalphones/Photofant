# STATE

**Aktiver Plan:** keiner — `docs/archive/2026-07/2026-07-07_p36-reverse-image-search/` (alle 4 Phasen
fertig, lint+build grün, archiviert 2026-07-08).

**Nächster Schritt (User-Reihenfolge, 2026-07-07):** `docs/planning/2026-07-07_p37-dinov2-reranking/`
starten → danach `2026-07-01_p22-knowledge-engine` bis `p26-recommendation-engine` (in
Nummernreihenfolge) → `2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`.

**Offen, User muss noch smoke-testen (P36 Phase 4, nicht blockierend für nächsten Plan):**
Text-Semantiksuche über den neuen Umschalter in der Suchbox — Checkliste in
`docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`
(Report-Back, Abschnitt „Smoke-Checkliste").

**Follow-ups aus P36 (🟡 nicht blockierend):**
- `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` seit Phase 3 ohne Aufrufer —
  eigener kleiner Cleanup bei Gelegenheit.
- `POST /api/search/semantic`s `query`-Zweig bleibt totes Backend-Duplikat (Entscheidung Phase 4,
  kein Auftrag zum Entfernen).

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
