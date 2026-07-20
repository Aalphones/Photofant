# ADR-027 — AI-Layer: Jobs fordern Fähigkeiten, nicht Modelle

**Status:** Angenommen — Phase 1 umgesetzt (P27 Phase 1: Capability-/Tool-Registry, Adapter, Prompt-Library)
**Datum:** 2026-07-20
**Betrifft:** Plan `2026-07-01_p27-gemma-integration`, nutzt Bestand aus P22 (`KnowledgeService`, Validator, Ownership), der Inferenz-Infra (`inference/`, `models/loader.py`) und ADR-008 (Feature per Setting abschaltbar)

> **ADR-Nummer:** Der Plan reservierte „ADR-013" — die Nummer war längst vergeben
> (comfyui-edit-als-asset). Wie bei P22 (010 belegt → 025) und P26 (012 belegt → 026)
> wird die nächste **echte** freie Nummer genommen: **027** (020 hält der geparkte
> P34-Plan, 021–026 existieren).

---

## Kontext

P27 bringt die erste LLM-Integration (Gemma). Jobs sollen Wissen mit KI-Unterstützung
pflegen, aber:

- Das konkrete Modell darf **nicht** in den Jobs verdrahtet sein — ein Modell-Swap
  (anderes Gemma, anderes lokales LLM) muss ohne Job-Änderung möglich sein (Konzept-ADR-005).
- Die KI darf die Wissensbasis **nie direkt** verändern (Konzept-ADR-006, P27-Sicherheitsregel):
  jede Persistenz läuft über `KnowledgeService` (Validator + Ownership + Markdown-first).
- Jede KI-Aktion muss **erklärbar** (Dok 040 §12) und **abschaltbar** (Konzept-ADR-008) sein.

## Optionen

- **Job ruft den Gemma-Adapter direkt:** verworfen — koppelt jeden Job ans Modell, ein
  Swap wird zur Find-and-Replace-Übung quer durch die Jobs.
- **Freie Tool-Nutzung durch die KI (die KI schreibt selbst):** verworfen — verletzt die
  Sicherheitsregel; die KI könnte am Validator/Ownership vorbei schreiben.
- **Capability-Registry + gefencte Tool-Registry (gewählt).**

## Entscheidung

**Jobs fordern eine `Capability`, nie ein Modell** (`inference/capabilities.py`):
`TEXT_GENERATION` · `KNOWLEDGE_IMPORT` · `KNOWLEDGE_UPDATE` · `INTERVIEW`. Die Zuordnung
Capability → Modell liegt im Setting `ai.capabilityMap` (leer = alles auf `ai.gemmaModel`).
Der Resolver liefert einen `TextGenerator` (Protokoll in `inference/interfaces.py`) — die
Naht, an der ein Modell-Swap eine reine Settings-/Adapter-Frage bleibt.

**Jede Fähigkeit bekommt nur die Werkzeuge, die sie braucht** (`inference/tools.py`,
`ToolRegistry`): `ReadMarkdown`, `SearchKnowledge`, `ValidatePatch`, `PatchEntity`. Alle
Persistenz geht durch `KnowledgeService`. `INTERVIEW` (private Personen, ADR-009) bekommt
**bewusst kein** Such-/Lese-Tool — eine private Entity wird nur aus den Interview-Antworten
gebaut, nicht mit Web-/Bestandswissen vermischt.

**Sicherheitsregel als Ablauf, nicht als Vertrauen:** Die KI **schlägt vor**. `ValidatePatch`
ist der Trockenlauf (`KnowledgeService.validate_patch`, prüft gegen die Domäne, schreibt
nicht), den der Nutzer sieht; erst nach Bestätigung schreibt der Job über `PatchEntity` /
den P25-Patch-Pfad. Kein Tool umgeht den Ownership-Check.

**Explainability-Payload** (`GenerationResult`): jeder Aufruf liefert Modell, Capability,
Prompt-Version, Dauer, Confidence — dasselbe „Herkunft/Begründung"-Prinzip wie die
P25-Korrektur-Historie und die P26-Reason-Chain.

**Abschaltbar pro Funktion** (`ai.autonomy`: `off` | `ask` | `auto`, Default `ask`). `off`
lässt das manuelle MVP (P22–P25) unverändert stehen.

## Konsequenzen

- Ein Modell-Swap ist eine Settings-/Adapter-Änderung, kein Job-Umbau — die Naht ist gebaut,
  nicht nachträglich zu suchen.
- Die KI kann strukturell nicht am Validator/Ownership vorbei schreiben; sie hat nur die
  Tools, die die Registry ihr gibt, und die schreiben ausschließlich über den Service.
- Confidence ist bei roher Textgenerierung `None` (ein LM liefert keine kalibrierte
  Sicherheit) — die Import-/Update-Fähigkeiten reichen später eine Patch-Confidence nach.
- Prompt-Änderungen sind versionierte Dateien (Prompt-Library), damit die Explainability
  eine Prompt-Version tragen kann und ein Prompt-Wechsel review-bar ist.
