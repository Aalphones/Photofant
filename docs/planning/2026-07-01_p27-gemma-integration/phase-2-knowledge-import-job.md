# Phase 2 — KnowledgeImportJob (Gemma füllt den Wizard-Vorschlag)

**Komplexität:** heikel · **Status:** complete

## Kontext
- README → Sicherheitsregel (Patch, kein Direct-Write) + Kontrakt
- Konzept: Dok 030 §13 (Gemma ersetzt den Wizard-Schritt, Struktur bleibt), Dok 020 §13, Konzept-ADR-006
- Phase 1: Capability/Tool-Registry, Gemma-Adapter, Prompts · **P23:** Wizard, Tasks · **P22:** Validator, `create_entity`
- Bestand: `jobs/queue.py`, `features/wissen/` (Wizard aus P23)

## AK
- [x] `KnowledgeImportJob` (Capability `KnowledgeImport`) erzeugt aus vorhandenem Kontext (Titel/Name, Typ, Domäne; optional verknüpfte Personen/Assets) einen **Vorschlag** — keinen Direkt-Write.
- [x] Der Vorschlag läuft durch den Validator (P22, `validate_entity`); ungültige Vorschläge werden abgewiesen (`suggestion: null` + `validation_errors`), nicht geschrieben.
- [x] Im Wizard: Aktion „KI-Vorschlag" füllt die Felder mit dem Vorschlag vor; der Nutzer ändert/bestätigt; erst „Speichern" schreibt (über den bestehenden `POST /knowledge/entities`, owner=user).
- [x] Nur öffentliche Domänen; private Entities laufen **nicht** hierüber (→ Phase 4). (Kein privater Import-Pfad; Import ist Anlege-Modus, nicht Edit.)
- [x] Explainability sichtbar (Modell, Prompt-Version, Confidence, Begründung) — im Wizard unter dem Button.
- [x] `ai.autonomy` = „aus" → keine „KI-Vorschlag"-Aktion (Button ausgeblendet + Backend-Guard 409); manueller Wizard (P23) unverändert.

## Umsetzung
- [x] `jobs/knowledge_import_job.py` + Registrierung (`JobKind.KNOWLEDGE_IMPORT`); nutzt Capability aus Phase 1
- [x] Wizard (P23) um „KI-Vorschlag"-Aktion + Vorbelegung + Explainability-Anzeige erweitert
- [x] Gemma-Vorschlag → Validator → Wizard-Vorbelegung (kein Auto-Write); Bestätigung = bestehender Wizard-Save
- [x] Job-Result-Kanal: `JobStatus.result`/`set_result` + `JobDto.result` + `Job.result` — der Vorschlag reist über den Job-Stream (Entscheidung: über den Job-Kanal statt eigenem Endpunkt); Store-Effekt `correlateSuggestionJob$` fischt ihn heraus
- [x] Neue Route `api/knowledge_ai.py` (`GET /knowledge/ai/autonomy`, `POST /knowledge/ai/import-suggestion`)
- [x] Doc: `docs/code-map.md`, `docs/routes.md`

## Ergebnis / Notizen
- **Vorschlag-Transport (heikle Stelle, mit User entschieden):** über den vorhandenen Job-Stream (`JobDto.result`), nicht über einen eigenen KI-Endpunkt. Generischer Mechanismus — Phase 3 (Update) und Phase 4 (Interview) erben ihn.
- **Gefüllte Felder:** primär die **Beschreibung** (Gemma-Absatz). Aliase/Beziehungen bleiben strukturell im Vorschlag, aber leer — ein rohes Text-LM liefert dafür nichts Verlässliches; ein reicherer Prompt kann sie später füllen, ohne den Kontrakt zu ändern.
- **Confidence:** feste `0.5` (SUGGESTION_CONFIDENCE) — rohe Generierung hat keine kalibrierte Confidence (Phase-1-FINDINGS); Nutzer-Bestätigung hebt auf 1.0 (owner=user).
