# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p24-photofant-integration/`
**Phase:** 3/3 — Verknüpfte Entity an Person/Asset (UI) (pending)
**Nächster Schritt:** `/clear`, dann `phase-3-media-links-surfaced.md` lesen (Kontext:
`features/personen/`, Asset-Detail, `models/person.model.ts`) und den Entity-Chip bauen.
Modell-Empfehlung: `sonnet` (Komplexität „mechanisch").

Phase 2 („Neue Person erkannt"-Affordance) ist fertig: Inline-Banner auf der Personen-Karte
(`features/personen/person-card/`), gespeist aus `store/knowledge`-Tasks, Wizard aus P23
wiederverwendet, Frontend-Typecheck + `ng build` grün. Finding für Phase 3 in FINDINGS.md:
`models/person.model.ts` hat `linked_entity` noch nicht nachgezogen, obwohl das Backend-DTO es
seit Phase 1 liefert.

Phase 1 (Entity-Linking + Job-Kette, Backend) ist fertig, `pytest`/`ruff` grün (368 passed,
13 vorbekannte Failures unverändert). Abweichungen vom Plan-Text dokumentiert in
`docs/planning/2026-07-01_p24-photofant-integration/FINDINGS.md` + `docs/decisions/014-…md`
(kein `ParentJobId`/`Depth`-Schleifenschutz gebaut — YAGNI, mit Nutzer abgestimmt; ADR-Nummer
011 war schon belegt).

Andere freigegebene, geparkte Pläne in `docs/planning/` (nach P24):
- `2026-07-01_p25-lore-panel/` — Lore-API + Panel-UI + Korrektur-Flow (braucht P24)
- `2026-07-01_p26-recommendation-engine/` — Empfehlungs-Job + Cards + Explainability (braucht P25)
- `2026-07-01_p27-gemma-integration/` — KI-Layer/Gemma-Adapter + Import/Update/Interview-Jobs (braucht P25)
- `2026-07-06_p34-mcp-wissensbasis/` — Entities/Beziehungen, Media-Links/Aufgaben, Lore/Empfehlungen, agentischer Workflow (braucht MCP-Basisplan + P24-P26)

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

**Smoke-Checkliste P23 (noch vom Nutzer zu prüfen — Details im archivierten P23-README):**
1. „Wissen" in der Nav öffnen → Wizard → Entity anlegen → Datei liegt im Vault.
2. Aufgabe per `curl POST .../tasks` anlegen → erscheint in der Work-Queue.
3. Aufgabe „Erledigen" → Wizard vorbelegt → speichern → Aufgabe verschwindet.
4. Zweiter Lookup zum selben Kontext → keine zweite Aufgabe.
