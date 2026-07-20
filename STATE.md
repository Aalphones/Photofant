# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p27-gemma-integration/`
**Phase:** 4/4 — Interview-Mode für private Entities (pending)
**Nächster Schritt:** Phase 4 starten — geführter Interview-Dialog im Wizard-Rahmen für
private Personen; aus den Antworten entsteht eine Markdown-Entity ohne Web-Vermischung
(ADR-009). FINDINGS für Phase 4 lesen (Autonomie-Gate-Muster an `interview` hängen,
`INTERVIEW`-Capability hat bewusst kein Such-/Lese-Tool, Schreibpfad via ToolRegistry).
Phase-4-Komplexität: heikel.

## Phase 1 erledigt (KI-Layer Backend)

Capability-/Tool-Registry, Gemma-Adapter (torch/transformers, ADR-028), Prompt-Library,
`ai.*`-Settings, Explainability-Payload. Compile + Import-Check grün. ADR-027/028 angelegt.

## Phase 2 erledigt (KI-Vorschlag im Wizard / Import)

`KnowledgeImportJob` (Gemma → Beschreibungs-Kandidat → Validator → Ergebnis über Job-Stream),
neuer Job-Result-Kanal (`JobStatus.result`/`set_result`, `JobDto.result`, `Job.result`),
`api/knowledge_ai.py` (`/ai/autonomy` + `/ai/import-suggestion`), Wizard „KI-Vorschlag"-Button
+ Vorbelegung + Explainability, NgRx `correlateSuggestionJob$`. tsc + ng build + ruff + mypy grün.

## Phase 3 erledigt (KI-Ergänzung im Lore Panel / Update)

`KnowledgeUpdateJob` (Gemma überarbeitet die bestehende Beschreibung → Validator-Trockenlauf
→ Ergebnis über Job-Stream), `api/knowledge_ai.py` um `/ai/update-suggestion` (anfordern) +
`/ai/update-suggestion/accept` (annehmen, `owner=inferred` fix — eigene Route statt der
user-fixen `/patch`) erweitert. Lore Panel „Ergänzen (KI)" neben „Das stimmt nicht" (gleiche
Ownership-Bedingung), Diff-Vorschau (alt→neu) + Begründung + Konfidenz, Annehmen/Ablehnen.
Backend-Tests für den Job (Proposal, kein Direkt-Write, Validierungs-Ablehnung, fehlende
Entity). tsc + ng build + ruff + pytest grün (13 vorbestehende rote Tests unverändert,
unabhängige Module — siehe Commit).

## Backlog (nach P27)

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan + P27 stehen.

## Smoke-Test P26 ausstehend (User)

Real-Check der Empfehlungs-Engine — Details:
`docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`.
