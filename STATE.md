# STATE

**Aktiver Plan:** (kein aktiver Plan)
**Stand:** P37 (DINOv2-Reranking + Duplikat-Scan) am 2026-07-08 abgeschlossen und nach
`docs/archive/2026-07/2026-07-07_p37-dinov2-reranking/` verschoben — alle 4 Phasen ✅, siehe README
dort für Summary/Deviations/Follow-ups.
**Nächster Schritt:** Laut User-Vorgabe (2026-07-07) ist `p22-knowledge-engine` als nächstes dran
(Nummernreihenfolge bis `p26-recommendation-engine` → `2026-07-06_p34-mcp-wissensbasis` →
`2026-07-01_p27-gemma-integration`). **Noch kein Plan-Dokument angelegt** — `docs/planning/` ist
aktuell leer; nächster Schritt ist `/plan` für `p22-knowledge-engine`, sobald daran gearbeitet wird.

**Offene Follow-ups (🟡, nicht blockierend):**
- Text-Semantiksuche-Umschalter smoke-testen — Checkliste in
  `docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`.
- `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` ohne Aufrufer (aus P36).
- `POST /api/search/semantic`s `query`-Zweig ist totes Backend-Duplikat (aus P36).
- P37-Smoke-Checklisten #1 (Rerank-Qualität) + #2 (Dupe-Schwellwert-Kalibrierung) stehen aus —
  Nutzer-Aufgabe am realen Bild-Set, siehe archiviertes P37-README.
- Ohne aktives DINOv2-Modell läuft kein automatischer Duplikat-Check mehr beim Import (bewusster
  Trade-off aus ADR-024, kein Fallback auf SigLIP2).
- 13 vorbestehende Test-Failures in `test_comfyui_run.py`/`test_comfyui_auto_import.py`/
  `test_caption_config.py` (Signatur-Drift `run_comfyui_run_job` fehlt `job_version_inputs`) —
  unabhängig von P37, nicht angefasst.
