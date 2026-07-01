# Phase 1 — AI-Layer + Gemma-Adapter + Prompt-Library (Backend)

**Komplexität:** heikel (Architektur-Abstraktion + Modell-Runtime-Entscheidung ADR-014) · **Status:** pending

## Kontext
- README → Kontrakt + Sicherheitsregel + Risiko Modell-Runtime
- Konzept: Dok 040 §2–7 (Capability/Tool-Registry, ModelManager), §5 (Lazy-Load), §10 (Prompt-Library), Konzept-ADR-004/005
- Bestand lesen: `inference/session_manager.py`, `inference/interfaces.py`, `models/loader.py`, `models/vram.py`, `inference/adapters/{joycaption,qwen_vl}.py` (Heavy-Lazy-Load-Muster), Modell-Management-Feature (`features/modelle/`, `api/models.py`), ggf. P19 (`../2026-06-30_p19-inference-session-pool.md`)

## AK
- [ ] `ai.gemmaModel` wird als Capability angesprochen: ein Job fordert `TextGeneration` an, kennt kein Modell (ADR-005/013).
- [ ] Gemma lädt **lazy** beim ersten Aufruf und entlädt nach `ai.idleTimeoutSeconds` (VRAM messbar wieder frei), integriert in die bestehende Session-/VRAM-Mechanik.
- [ ] Capability-Registry mappt `TextGeneration`/`KnowledgeImport`/`KnowledgeUpdate`/`Interview` → Gemma; Tool-Registry stellt die erlaubten Werkzeuge bereit (`ReadMarkdown`, `SearchKnowledge`, `PatchEntity`, `ValidatePatch`), alle Persistenz über `KnowledgeService`.
- [ ] Prompt-Library als Markdown unter `ai.promptLibraryPath` geladen; Prompt-Version abrufbar (für Explainability).
- [ ] Ein Test-/Demo-Aufruf generiert Text und liefert die Explainability-Payload (Modell, Capability, Prompt-Version, Dauer, Confidence).
- [ ] **ADR-014 entschieden + dokumentiert** (Runtime torch vs. GGUF, Begründung, Lizenz-/Offline-Check).

## Umsetzung
- [ ] `inference/capabilities.py` (Registry) + `inference/tools.py` (Tool-Registry)
- [ ] `inference/adapters/gemma.py` (Lazy-Load/Idle-Unload über `session_manager`, VRAM-gated)
- [ ] ModelManager-Anbindung (Capability→Modell), an bestehende `models/loader.py`/`vram.py`
- [ ] `knowledge/prompts/` Markdown-Library + Loader (Version = Datei-Metadatum/Header)
- [ ] settings-Keys `ai.*`; Modell-Bezug über Modell-Management-Feature (Download/In-Place/Gating), kein Repo-Binary
- [ ] Doc: `docs/code-map.md` (AI-Layer), `docs/decisions/013-ai-capability-layer.md`, `docs/decisions/014-gemma-runtime.md`
