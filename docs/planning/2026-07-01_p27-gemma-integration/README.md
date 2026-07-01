# P27 — Gemma-Integration (KI-gestützte Wissenspflege)

> Roadmap-Phase 6 (Dok 040 AI Architecture, Dok 020 §13 KI-Patches, Dok 030 §13, Konzept-ADR-005/006/009). **Erste LLM-Integration.** Baut auf **P22** (Service/Validator/Patch) + **P23** (Wizard/Tasks) + **P25** (Patch-UI/Explainability) auf; koexistiert mit P26. Nutzt die vorhandene Inferenz-Infra (`inference/session_manager.py`, `models/loader.py`, VRAM-Management, Modell-Management-Feature). *(private, lean.)*

## Ziel
Gemma unterstützt das Anlegen und Pflegen von Wissen — füllt den Wizard automatisch, schlägt Ergänzungen zu bestehenden Entities vor, führt für private Personen einen Interview-Dialog. **Gemma ändert nie direkt Daten** (Konzept-ADR-006): es erzeugt ausschließlich Patches, die durch den Validator (P22) laufen und die der Nutzer bestätigt, bevor sie ins Markdown geschrieben werden. Die Job-/Wizard-/Patch-Struktur aus P22–P25 bleibt identisch — Gemma ersetzt nur den manuellen Denk-Schritt.

## Zentrale Sicherheitsregel (nicht verhandelbar)
```
Entity/Kontext → Gemma → Patch → Validator → Nutzer bestätigt → Service schreibt Markdown → Cache
```
Gemma sieht immer nur den aktuell nötigen Kontext (Dok 001 §4), besitzt kein dauerhaftes Wissen. Jede KI-Aktion ist abschaltbar (Konzept-ADR-008) und erklärbar (Dok 040 §12).

## Scope
**Drin:** AI-Layer — Capability- + Tool-Registry + ModelManager-Anbindung, Gemma-Adapter mit Lazy-Load/Idle-Unload · Prompt-Library als Markdown (`knowledge/prompts/`) · `KnowledgeImportJob` (Gemma füllt Wizard-Vorschlag) · `KnowledgeUpdateJob` (Gemma schlägt Ergänzungen vor) · Interview-Mode für private Entities (ADR-009).
**Draußen:** Creative-Jobs/ComfyUI-Intelligenz → Roadmap-Phase 7 · Discovery → Phase 8 · autonome Hintergrundverarbeitung (bleibt bewusst aus, ADR-010 des Konzepts).

## Abhängigkeiten
**P22** (Service, Validator, Patch-Pfad) · **P23** (Wizard, Task-Queue) · **P25** (Patch-UI, Explainability-Element). Nutzt Bestand: `inference/` (session_manager, interfaces), `models/loader.py`/`vram.py`, Modell-Management-Feature (Download/In-Place/Gating), Muster der Heavy-Captioner (JoyCaption/Qwen-VL laufen schon über torch/transformers + Lazy-Load).

## Kontrakt-Ergänzungen
- **Capability-Registry** (`inference/capabilities.py`): Jobs fordern eine Fähigkeit an (`TextGeneration`, `KnowledgeImport`, `KnowledgeUpdate`, `Interview`), nie ein Modell (Konzept-ADR-005). ModelManager bildet Capability → Modell ab.
- **Tool-Registry** (`inference/tools.py`): die Werkzeuge, die eine Capability nutzen darf (`ReadMarkdown`, `SearchKnowledge`, `PatchEntity`, `ValidatePatch` …) — kapseln Implementierung, alle Persistenz über `KnowledgeService`.
- **Gemma-Adapter** (`inference/adapters/gemma.py`): Lazy-Load über `session_manager`, Idle-Unload nach Timeout, VRAM-gated wie andere Heavy-Modelle.
- **Jobs:** `jobs/knowledge_import_job.py`, `jobs/knowledge_update_job.py` — produzieren **Patches**, nie Direkt-Writes; Patch geht durch Validator (P22) und landet als Vorschlag beim Nutzer (Wizard/Panel).
- **Explainability** (erweitert die P26-geteilte Payload): jeder KI-Aufruf liefert Modell, Capability, Prompt-Version, Dauer, Confidence, Begründung (Dok 040 §12).

## Reservierte Entscheidungen & Settings
**ADR (real anlegen; nächste freie nach ADR-012 = 013, 014):**
- **ADR-013** — AI-Layer: Capability-/Tool-Registry + ModelManager; Jobs kennen nur Fähigkeiten.
- **ADR-014** — Gemma-Laufzeit (🔴 **offene Entscheidung, in Phase 1 zu fällen**): torch/transformers (wie Heavy-Captioner) **vs.** GGUF-Runtime (llama.cpp) auf RTX 3060; Prompt-Library als Markdown. Lizenz-/Offline-Constraints prüfen (Gemma-Terms, `HF_HUB_OFFLINE`, keine Binaries im Repo — Bezug nur über Settings-UI).

**settings.json (vorab freigeben):** `ai.gemmaModel` (Binding/Variante) · `ai.idleTimeoutSeconds` (Idle-Unload) · `ai.capabilityMap` (Capability→Modell) · `ai.autonomy` (pro Funktion: aus/nachfragen/auto — Konzept-ADR-008) · `ai.promptLibraryPath` (Default `<vault>/prompts`).

## Design-Lage (freihändig — freigegeben)
Kein Mockup. KI-Vorschläge erscheinen **im vorhandenen** Wizard (P23) und Lore Panel (P25) als vorausgefüllte, bestätigungspflichtige Vorschläge — kein neuer Screen, kein Chat (Dok 050 §13). Interview-Mode ist ein geführter Dialog im Wizard-Rahmen.

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | AI-Layer + Gemma-Adapter + Prompt-Library (Backend) | heikel (Architektur + Modell-Runtime-Entscheidung) | pending |
| 2 | KnowledgeImportJob — Gemma füllt den Wizard-Vorschlag | heikel | pending |
| 3 | KnowledgeUpdateJob — Ergänzungs-Vorschläge im Lore Panel | standard | pending |
| 4 | Interview-Mode für private Entities | heikel | pending |

## Finale AK (Gesamt)
- [ ] Ein Job fordert eine Capability an (nicht ein Modell); der ModelManager lädt Gemma lazy, generiert, und entlädt nach Idle-Timeout (VRAM wieder frei — nachweisbar).
- [ ] Beim Anlegen einer öffentlichen Entity kann der Nutzer einen KI-Vorschlag anfordern; Gemma füllt die Wizard-Felder als **Vorschlag**, der Nutzer bestätigt/ändert vor dem Schreiben.
- [ ] Zu einer bestehenden Entity schlägt Gemma Ergänzungen als Patch vor; nichts wird ohne Bestätigung geschrieben; jede Änderung ist erklärbar (Modell, Prompt-Version, Confidence, Begründung).
- [ ] Für eine private Person führt Gemma einen Interview-Dialog; aus den Antworten entsteht eine Markdown-Entity, ohne Web-Vermischung (ADR-009).
- [ ] Jede KI-Funktion ist in den Einstellungen abschaltbar (aus/nachfragen/auto); bei „aus" verhält sich das System wie das manuelle MVP (P22–P25).
- [ ] Offline-Garantie gewahrt: Modellbezug nur über die Settings-UI, keine Laufzeit-Netzwerkzugriffe.

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. Einen Job mit Capability `TextGeneration` auslösen → im Modell-/Job-Dock sehen: Gemma lädt, generiert, entlädt nach Idle (VRAM-Anzeige fällt zurück).
2. Im Wizard „KI-Vorschlag" für eine bekannte öffentliche Person → Felder vorausgefüllt; ändern + bestätigen → Markdown entspricht der Bestätigung, nicht dem Rohvorschlag.
3. Im Lore Panel „Ergänzen (KI)" → Patch-Vorschlag → ablehnen → Markdown unverändert; annehmen → Änderung + Explainability-Eintrag.
4. Interview-Mode für eine private Person durchklicken → Entity entsteht, `owner`/`domain` privat, keine Web-Quellen.
5. `ai.autonomy` einer Funktion auf „aus" → die KI-Aktion ist nicht mehr angeboten; manuelle Wege funktionieren weiter.

## Risiken
- 🟡 **Modell-Runtime-Entscheidung (ADR-014)** — torch/transformers vs. GGUF auf RTX 3060; VRAM-Konkurrenz mit Captioner/Generativ-Modellen. Mitigation: Lazy-Load + Idle-Unload strikt, an bestehende VRAM-/Session-Mechanik hängen (ggf. P19 Session-Pool berücksichtigen), Phase 1 entscheidet und dokumentiert.
- 🟡 **Halluzinierte/falsche Patches** — Gemma erzeugt plausiblen Unfug. Mitigation: **nie** Direkt-Write (ADR-006), Validator + Pflicht-Bestätigung, Confidence sichtbar, Ownership schützt user-Werte.
- 🟡 **Privat/öffentlich-Vermischung** (ADR-009) — private Entities dürfen nicht web-recherchiert/vermischt werden. Mitigation: getrennte Capability (`Interview`) ohne Web-Tools, kein Import-Pfad für private Domänen.
- 🟡 **Prompt-Drift ohne Versionierung** — Dok 040 §14 offen. Mitigation: Prompt-Library als versionierte Markdown-Dateien, Prompt-Version in der Explainability-Payload.

## Chesterton
**Vor Nutzung verstehen:** die Heavy-Modell-Ladung (`inference/session_manager.py`, `models/loader.py`, `models/vram.py`) und wie JoyCaption/Qwen-VL lazy geladen + entladen werden — Gemma folgt exakt diesem Muster, kein neuer Lade-Pfad. Der Patch-/Validator-/Ownership-Pfad aus P22/P25 wird **wiederverwendet**, nicht ersetzt: Gemma ist eine neue Patch-*Quelle*, das Schreiben bleibt beim Service.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_ — Follow-ups: Creative-Jobs/ComfyUI-Intelligenz (Roadmap-Phase 7) · Discovery (Phase 8) · Prompt-Versionierungs-Strategie ausbauen.
