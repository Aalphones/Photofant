# STATE

**Aktiver Plan:** _(kein aktiver Plan)_ — P22 Knowledge Engine ist **komplett fertig + archiviert**
(`docs/archive/2026-07/2026-07-01_p22-knowledge-engine/`, alle 4 Phasen ✅).

**Nächster Schritt:** Backlog-Plan wählen und mit `/implement` starten. Freigegebene, geparkte Pläne
in `docs/planning/`:
- `2026-07-01_p23-knowledge-wizard/` — Task-Queue + Wizard-UI + Work-Queue-UI
- `2026-07-01_p24-photofant-integration/` — Entity-Linking, Personen-Affordance, Media-Links
- `2026-07-01_p25-lore-panel/` — Lore-API + Panel-UI + Korrektur-Flow
- `2026-07-01_p26-recommendation-engine/` — Empfehlungs-Job + Cards + Explainability
- `2026-07-01_p27-gemma-integration/` — KI-Layer/Gemma-Adapter + Import/Update/Interview-Jobs
- `2026-07-06_p34-mcp-wissensbasis/` — Entities/Beziehungen, Media-Links/Aufgaben, Lore/Empfehlungen, agentischer Workflow

P23–P27 lesen den P22-Kontrakt (README-Sektion „Kontrakt", jetzt im Archiv) als Single Source.

**Offene Follow-ups (🟡, nicht blockierend):**
- P22: Markdown-Embeddings / semantische Wissenssuche (bewusst nach hinten) · Relationship-Metadaten
  falls P26 es braucht · inkrementeller Reconcile mit `synced_at`-Spalte erst wenn der Vault groß wird.
- Text-Semantiksuche-Umschalter smoke-testen — Checkliste in
  `docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`.
- `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` ohne Aufrufer (aus P36).
- `POST /api/search/semantic`s `query`-Zweig ist totes Backend-Duplikat (aus P36).
- P37-Smoke-Checklisten #1 (Rerank-Qualität) + #2 (Dupe-Schwellwert-Kalibrierung) stehen aus —
  Nutzer-Aufgabe am realen Bild-Set, siehe archiviertes P37-README.
- Ohne aktives DINOv2-Modell läuft kein automatischer Duplikat-Check mehr beim Import (ADR-024).
- 13 vorbestehende Test-Failures in `test_comfyui_run.py`/`test_comfyui_auto_import.py`/
  `test_caption_config.py` (Signatur-Drift `run_comfyui_run_job` fehlt `job_version_inputs`).
- 124 vorbestehende `mypy --strict`-Fehler quer über die Codebase — kein Vollprojekt-Grün-Gate aktiv.
