# Phase 4 — Interview-Mode für private Entities

**Komplexität:** heikel (Dialog-Flow + strikte Privat/Öffentlich-Trennung) · **Status:** pending

## Kontext
- README → Sicherheitsregel + Kontrakt · Konzept: Dok 040 §11, Dok 050 §11, Konzept-ADR-009
- Phase 1: AI-Layer (Capability `Interview`, **ohne** Web-Tools) · **P23:** Wizard-Rahmen · **P22:** `create_entity`
- Bestand: `features/wissen/` (Wizard)

## AK
- [ ] Für eine private Person/Haustier führt Gemma einen geführten Dialog (Wer ist die Person? Beziehung? Wichtige Ereignisse? — Dok 050 §11) im Wizard-Rahmen, kein freies Chat-Fenster.
- [ ] Aus den Antworten entsteht ein Entity-Patch → Validator → Nutzer bestätigt → Markdown-Entity (`owner`/`domain` privat).
- [ ] **Keine Web-Vermischung** (ADR-009): die `Interview`-Capability hat keine Web-/Import-Tools; private Domänen laufen nie über `KnowledgeImportJob` (Phase 2).
- [ ] Explainability wie sonst; `ai.autonomy` = „aus" → nur manueller Wizard (P23).

## Umsetzung
- [ ] Interview-Capability-Prompt(s) in der Prompt-Library
- [ ] Dialog-Flow im Wizard (`features/wissen/`): Frage → Antwort → nächste Frage → Zusammenfassung → Bestätigung
- [ ] Antworten → Patch → Validator → `create_entity` (privat)
- [ ] Guard: private Domänen von `KnowledgeImportJob` ausgeschlossen (Test/Assertion)
- [ ] Doc: `docs/code-map.md`
- [ ] **Gesamt-P27:** finale AK + Smoke-Checkliste der README gegenprüfen
