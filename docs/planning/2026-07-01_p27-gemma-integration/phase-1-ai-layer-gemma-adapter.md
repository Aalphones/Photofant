# Phase 1 — AI-Layer + Gemma-Adapter + Prompt-Library (Backend)

**Komplexität:** heikel (Architektur-Abstraktion + Modell-Runtime-Entscheidung ADR-028) · **Status:** complete

## Kontext
- README → Kontrakt + Sicherheitsregel + Risiko Modell-Runtime
- Konzept: Dok 040 §2–7 (Capability/Tool-Registry, ModelManager), §5 (Lazy-Load), §10 (Prompt-Library), Konzept-ADR-004/005
- Bestand lesen: `inference/session_manager.py`, `inference/interfaces.py`, `models/loader.py`, `models/vram.py`, `inference/adapters/{joycaption,qwen_vl}.py` (Heavy-Lazy-Load-Muster), Modell-Management-Feature (`features/modelle/`, `api/models.py`), ggf. P19 (`../2026-06-30_p19-inference-session-pool.md`)

## AK
- [x] `ai.gemmaModel` wird als Capability angesprochen: ein Job fordert `TextGeneration` an, kennt kein Modell (ADR-005/027).
- [x] Gemma lädt **lazy** beim ersten Aufruf und entlädt nach `ai.idleTimeoutSeconds` (VRAM messbar wieder frei), integriert in die bestehende Session-/VRAM-Mechanik.
- [x] Capability-Registry mappt `TextGeneration`/`KnowledgeImport`/`KnowledgeUpdate`/`Interview` → Gemma; Tool-Registry stellt die erlaubten Werkzeuge bereit (`ReadMarkdown`, `SearchKnowledge`, `PatchEntity`, `ValidatePatch`), alle Persistenz über `KnowledgeService`.
- [x] Prompt-Library als Markdown geladen (`ai.promptLibraryPath` sonst mitgelieferte Defaults); Prompt-Version abrufbar (für Explainability).
- [x] Ein Aufruf über `capabilities.generate()` liefert die Explainability-Payload (`GenerationResult`: Modell, Capability, Prompt-Version, Dauer, Confidence).
- [x] **ADR-028 entschieden + dokumentiert** (Runtime torch vs. GGUF, Begründung, Lizenz-/Offline-Check). Entscheidung: torch/transformers.

## Umsetzung
- [x] `inference/capabilities.py` (Registry) + `inference/tools.py` (Tool-Registry)
- [x] `inference/adapters/gemma.py` (Lazy-Load/Idle-Unload über `generative_engine`, VRAM-gated)
- [x] Capability→Modell über `ai.capabilityMap`/`ai.gemmaModel` → `ModelRegistry` (wie `resolve_joycaption`)
- [x] Prompt-Library + Loader (`inference/prompt_library.py`; Version = Frontmatter-Header, Prompts unter `inference/prompts/`)
- [x] settings-Keys `ai.*`; Modell-Bezug über Modell-Management-Feature (Manifest `gemma-3-4b-it`, `requires_license_ack`), kein Repo-Binary
- [x] Doc: `docs/code-map.md` (KI-Layer), `docs/decisions/027-ai-capability-layer.md`, `docs/decisions/028-gemma-runtime.md`
