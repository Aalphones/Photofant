# Phase 2 — KnowledgeImportJob (Gemma füllt den Wizard-Vorschlag)

**Komplexität:** heikel · **Status:** pending

## Kontext
- README → Sicherheitsregel (Patch, kein Direct-Write) + Kontrakt
- Konzept: Dok 030 §13 (Gemma ersetzt den Wizard-Schritt, Struktur bleibt), Dok 020 §13, Konzept-ADR-006
- Phase 1: Capability/Tool-Registry, Gemma-Adapter, Prompts · **P23:** Wizard, Tasks · **P22:** Validator, `create_entity`
- Bestand: `jobs/queue.py`, `features/wissen/` (Wizard aus P23)

## AK
- [ ] `KnowledgeImportJob` (Capability `KnowledgeImport`) erzeugt aus vorhandenem Kontext (Personenname, verknüpfte Bilder, ausgewählte Domäne) einen **Entity-Patch-Vorschlag** — keinen Direkt-Write.
- [ ] Der Vorschlag läuft durch den Validator (P22); ungültige Vorschläge werden abgewiesen, nicht geschrieben.
- [ ] Im Wizard: Aktion „KI-Vorschlag" füllt die Felder mit dem Vorschlag vor; der Nutzer ändert/bestätigt; erst „Speichern" schreibt (über `KnowledgeService`, owner bleibt korrekt gesetzt).
- [ ] Nur öffentliche Domänen; private Entities laufen **nicht** hierüber (→ Phase 4).
- [ ] Explainability sichtbar (Modell, Prompt-Version, Confidence, Begründung).
- [ ] `ai.autonomy` = „aus" → keine „KI-Vorschlag"-Aktion; manueller Wizard (P23) unverändert.

## Umsetzung
- [ ] `jobs/knowledge_import_job.py` + Registrierung; nutzt Capability + Tools aus Phase 1
- [ ] Wizard (P23) um „KI-Vorschlag"-Aktion + Vorbelegung + Explainability-Anzeige erweitern
- [ ] Patch → Validator → Wizard-Vorbelegung (kein Auto-Write); Bestätigung = bestehender Wizard-Save
- [ ] Doc: `docs/code-map.md`, `docs/routes.md` (falls neue Route)
