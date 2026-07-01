# Phase 3 — KnowledgeUpdateJob (Ergänzungs-Vorschläge im Lore Panel)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Sicherheitsregel + Kontrakt
- Konzept: Dok 060 Phase 6 (Knowledge Update), Konzept-ADR-006
- Phase 1: AI-Layer · **P25:** Patch-UI + Explainability-Element (wiederverwenden!) · **P22:** Validator, `update_entity`
- Bestand: `jobs/queue.py`, Lore Panel (P25)

## AK
- [ ] `KnowledgeUpdateJob` (Capability `KnowledgeUpdate`) schlägt zu einer bestehenden Entity Ergänzungen/Korrekturen als **Patch** vor (kein Direkt-Write).
- [ ] Im Lore Panel: Aktion „Ergänzen (KI)" → Patch-Vorschlag mit Diff (alt→neu) + Begründung; **Ablehnen** lässt Markdown unverändert, **Annehmen** schreibt über den P25-Patch-Pfad + erzeugt Explainability-Eintrag.
- [ ] Ownership gewahrt: user-Werte werden nicht durch inferred-Vorschläge überschrieben (Vorschlag markiert, nicht erzwungen).
- [ ] Nutzt das **geteilte** Explainability-Element (P26 Phase 3) — keine zweite Implementierung.
- [ ] `ai.autonomy` = „aus" → Aktion nicht angeboten.

## Umsetzung
- [ ] `jobs/knowledge_update_job.py` + Registrierung
- [ ] Lore Panel (P25) um „Ergänzen (KI)" + Diff-Vorschau erweitern; Annehmen = bestehender PatchJob-Pfad
- [ ] Doc: `docs/code-map.md`
