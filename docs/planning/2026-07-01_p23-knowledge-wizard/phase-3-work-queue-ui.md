# Phase 3 — Work-Queue-UI (offene Aufgaben)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Design-Lage + Kontrakt · Konzept Dok 050 §12/§4/§13
- Phase 1: Task-REST · Phase 2: `features/wissen/`, Store, Service, Wizard
- Bestand: Queue-Muster `features/review/`, `ui/job-dock/`

## AK
- [ ] Sicht listet offene Aufgaben (`GET .../tasks?status=open`), erkennbar nach `kind`.
- [ ] Primäraktion „Erledigen" → öffnet Wizard mit vorbelegtem Kontext (z.B. Titel aus Personenname).
- [ ] Nach erfolgreichem Anlegen → Aufgabe `resolved`, verschwindet aus der offenen Liste.
- [ ] Sekundär „Später" (offen) + „Ignorieren" (dismissed) (Dok 050 §4).
- [ ] Leerer Zustand freundlich erklärt.

## Umsetzung
- [ ] `features/wissen/` um Work-Queue-Komponente erweitern
- [ ] `store/knowledge/` um Task-State (Slice aus Phase 2 wiederverwenden — kein zweiter Store)
- [ ] `services/knowledge.service.ts` um Task-Calls
- [ ] Wizard-Öffnen mit Vorbelegung; nach Success Task-resolve
- [ ] Doc: `docs/code-map.md`
- [ ] **Gesamt-P23:** finale AK + Smoke-Checkliste der README gegenprüfen
