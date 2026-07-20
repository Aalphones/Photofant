# Phase 4 — Interview-Mode für private Entities

**Komplexität:** heikel (Dialog-Flow + strikte Privat/Öffentlich-Trennung) · **Status:** ✅ complete

> **Design-Entscheidung (mit User bestätigt):** Der Dialog läuft als **festes Fragen-Skript**
> (Frontend, eine Frage pro Schritt) + **einmalige Synthese** (ein `InterviewJob` fasst die
> Antworten zusammen) — nicht Gemma-getrieben turn-by-turn. Grund: „kein freies Chat" (AK) +
> ein rohes 4B-Text-LM ist beim Turn-für-Turn-Führen/„genug gewusst"-Entscheiden unzuverlässig
> (FINDINGS Phase 2/3), aber zuverlässig beim Zusammenfassen gegebener Fakten. Der
> `interview.md`-Prompt wurde entsprechend von „live interview" auf „Synthese" umgeschrieben (v2).

## Kontext
- README → Sicherheitsregel + Kontrakt · Konzept: Dok 040 §11, Dok 050 §11, Konzept-ADR-009
- Phase 1: AI-Layer (Capability `Interview`, **ohne** Web-Tools) · **P23:** Wizard-Rahmen · **P22:** `create_entity`
- Bestand: `features/wissen/` (Wizard)

## AK
- [x] Für eine private Person/Haustier führt Gemma einen geführten Dialog (Wer ist die Person? Beziehung? Wichtige Ereignisse? — Dok 050 §11) im Wizard-Rahmen, kein freies Chat-Fenster. → festes Skript im `pf-interview-dialog`, Frage pro Schritt.
- [x] Aus den Antworten entsteht ein Entity-Patch → Validator → Nutzer bestätigt → Markdown-Entity (`owner`/`domain` privat). → `InterviewJob` synthetisiert Body → Validator-Trockenlauf → Bestätigung legt via `POST /entities` an (`owner=user`, private Domäne).
- [x] **Keine Web-Vermischung** (ADR-009): die `Interview`-Capability hat keine Web-/Import-Tools; private Domänen laufen nie über `KnowledgeImportJob` (Phase 2). → Guard `_is_private_domain` in `import-suggestion` (422); Interview-Route erzwingt private Domäne.
- [x] Explainability wie sonst; `ai.autonomy` = „aus" → nur manueller Wizard (P23). → Interview-Route 409 bei `off`, Button ausgeblendet.

## Umsetzung
- [x] Interview-Capability-Prompt(s) in der Prompt-Library → `interview.md` v2 (Synthese).
- [x] Dialog-Flow im Wizard (`features/wissen/`): Frage → Antwort → nächste Frage → Zusammenfassung → Bestätigung → `interview-dialog/`.
- [x] Antworten → Patch → Validator → `create_entity` (privat) → über den Job → Bestätigung → `POST /entities`.
- [x] Guard: private Domänen von `KnowledgeImportJob` ausgeschlossen (Test/Assertion) → `test_knowledge_ai_private_guard.py`.
- [x] Doc: `docs/code-map.md` (+ `routes.md`, inkl. nachgezogener Phase-3-Routen).
- [x] **Gesamt-P27:** finale AK + Smoke-Checkliste der README gegenprüfen → Smoke-Checkliste an den User (Plan-Ende).

## Getestet
- `test_interview_job.py` — Synthese aus Antworten, kein Vault-Write, leere Modell-Ausgabe wirft, Validator-Abweisung behält Explainability, Prompt nutzt nur beantwortete Fragen.
- `test_knowledge_ai_private_guard.py` — private.yaml parst als privat, `_is_private_domain`, Import lehnt private Domäne ab (422), Interview lehnt öffentliche Domäne ab (422).
- Bestand nachgezogen: `test_knowledge_api.py::test_list_domains_returns_seeded_domains` (jetzt Movies **und** Private, mit `private`-Flag).
- Gates grün: ruff · mypy · pytest (Phase-4-Umfang) · tsc · ng build. (3 rote `comfyui_run`-Batch-Tests sind Bestand, unberührtes Modul.)
