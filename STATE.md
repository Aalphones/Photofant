# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p27-gemma-integration/` — **alle 4 Phasen ✅ complete**
**Phase:** 4/4 — Interview-Mode für private Entities (✅ complete, committet)
**Nächster Schritt:** Plan-Ende. Ausstehend: (1) User-Smoke von P27 (Checkliste in der
README, Wackelstellen zuerst) — Gemma muss dafür geladen/verfügbar sein; (2) Archivieren
nach grünem Smoke (`git mv` → `docs/archive/2026-07/`, README-Bottom-Sektionen füllen).
Danach STATE auf den nächsten Plan zeigen (Backlog: p34-mcp-wissensbasis, blockiert).

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

- `docs/planning/2026-07-20_p35-gemma-gguf-runtime/` — **freigegeben, geparkt.** Bindet das lokale
  GGUF-Gemma (12B, `D:\Models\OBLITERATUS\…`) als 2. Runtime neben torch (ADR-028 ergänzt, nicht
  revidiert); Vision-Naht (mmproj) vorgesehen, Feature Backlog. 3 Phasen, Phase 1 heikel. Start: `/implement`.
- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan + P27 stehen.

## Smoke-Test P26 ausstehend (User)

Real-Check der Empfehlungs-Engine — Details:
`docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`.
