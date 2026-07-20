# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p27-gemma-integration/`
**Phase:** 3/4 — KnowledgeUpdateJob: Ergänzungs-Vorschläge im Lore Panel (pending)
**Nächster Schritt:** Phase 3 starten — Gemma schlägt zu einer bestehenden Entity Ergänzungen
als Patch vor; „Ergänzen (KI)" im Lore Panel (P25) zeigt sie, Annehmen schreibt über den
P25-Patch-Pfad (`enqueue_knowledge_patch`, owner=inferred/web). FINDINGS für Phase 3 lesen
(Job-Result-Kanal + Autonomie-Gate stehen aus Phase 2, Confidence-Ableitung, Schreibpfad via
ToolRegistry). Phase-3-Komplexität: standard.

## Phase 1 erledigt (KI-Layer Backend)

Capability-/Tool-Registry, Gemma-Adapter (torch/transformers, ADR-028), Prompt-Library,
`ai.*`-Settings, Explainability-Payload. Compile + Import-Check grün. ADR-027/028 angelegt.

## Phase 2 erledigt (KI-Vorschlag im Wizard / Import)

`KnowledgeImportJob` (Gemma → Beschreibungs-Kandidat → Validator → Ergebnis über Job-Stream),
neuer Job-Result-Kanal (`JobStatus.result`/`set_result`, `JobDto.result`, `Job.result`),
`api/knowledge_ai.py` (`/ai/autonomy` + `/ai/import-suggestion`), Wizard „KI-Vorschlag"-Button
+ Vorbelegung + Explainability, NgRx `correlateSuggestionJob$`. tsc + ng build + ruff + mypy grün.

## Backlog (nach P27)

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan + P27 stehen.

## Smoke-Test P26 ausstehend (User)

Real-Check der Empfehlungs-Engine — Details:
`docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`.
