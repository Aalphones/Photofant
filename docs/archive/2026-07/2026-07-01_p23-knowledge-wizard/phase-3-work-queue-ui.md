# Phase 3 — Work-Queue-UI (offene Aufgaben)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Design-Lage + Kontrakt · Konzept Dok 050 §12/§4/§13
- Phase 1: Task-REST · Phase 2: `features/wissen/`, Store, Service, Wizard
- Bestand: Queue-Muster `features/review/`, `ui/job-dock/`

## AK
- [x] Sicht listet offene Aufgaben (`GET .../tasks?status=open`), erkennbar nach `kind`.
- [x] Primäraktion „Erledigen" → öffnet Wizard mit vorbelegtem Kontext (z.B. Titel aus Personenname).
- [x] Nach erfolgreichem Anlegen → Aufgabe `resolved`, verschwindet aus der offenen Liste.
- [x] Sekundär „Später" (offen) + „Ignorieren" (dismissed) (Dok 050 §4).
- [x] Leerer Zustand freundlich erklärt.

## Umsetzung
- [x] `features/wissen/` um Work-Queue-Komponente erweitert (`work-queue/`)
- [x] `store/knowledge/` um Task-State erweitert (zweiter EntityAdapter im selben `KnowledgeState`, siehe FINDINGS.md — kein zweiter Store)
- [x] `services/knowledge.service.ts` um Task-Calls (`listTasks`, `resolveTask`, `dismissTask`)
- [x] Wizard-Öffnen mit Vorbelegung; nach Success Task-resolve
- [x] Doc: `docs/code-map.md`
- [x] **Gesamt-P23:** finale AK + Smoke-Checkliste der README gegenprüfen

## Abweichungen vom Plan
- „Später" ändert den Task-Status nicht (Backend kennt keinen dritten Übergang aus `open`)
  — blendet den Task nur session-lokal (clientseitiges `Set<number>`) aus der Liste aus, bis
  neu geladen wird. Deckt die AK „Später (offen)" ab, ohne einen Backend-Kontrakt zu ändern.
