# Phase 2 — „Neue Person erkannt"-Affordance (UI)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Design-Lage + Screen-Eigentümer-Regel · Konzept Dok 050 §4/§13
- Phase 1: link-Routen, Trigger · **P23:** Wizard, Tasks, `features/wissen/`
- Bestand: `features/personen/`, `features/review/` (wahrscheinlichster Ort), `store/persons/`, `services/person.service.ts`

## Screen-Entscheidung
`features/personen/` (Personen-Karte), **nicht** `features/review/`. Begründung: der Trigger
(`api/review_queue.py`, Person-Bestätigung in der Review-Faces-Queue) feuert asynchron
(`asyncio.ensure_future`) — bis die Aufgabe entsteht, hat die Review-Queue oft schon zum
nächsten Gesicht weitergeblättert. Die Personen-Karte ist dagegen die dauerhafte Repräsentation
der Person (Umbenennen, Gruppieren, Löschen leben dort) und bleibt sichtbar, solange die
Aufgabe offen ist — passt zur Screen-Eigentümer-Regel besser als ein transientes Element in
der Review-Queue.

## AK
- [x] Neu erkannte/bestätigte Person ohne Entity → dezenter Inline-Hinweis „🆕 Neue Person — Wissen anlegen?" mit drei Aktionen: **Wissen anlegen** (Wizard aus P23, Titel = Personenname vorbelegt), **Später** (Aufgabe bleibt offen), **Ignorieren** (dismissed).
- [x] „Wissen anlegen" → nach Anlegen Person mit Entity verknüpft (Phase-1-Route), Hinweis weg.
- [x] Kein Popup-Zwang — ruhiges Inline-Element, wegklickbar.
- [x] Fügt sich in die Struktur des besitzenden Screens ein, kein Wegwerf-Container.

## Umsetzung
- [x] Inline-Affordance in `features/personen/person-card/` (Screen-Entscheidung s.o.) — neue Zeile
  im bestehenden `person-card__meta`-Block, kein Extra-Container.
- [x] Verdrahtung: Wizard öffnen (Vorbelegung aus `task.context.ref`) → nach Success
  `PersonService.linkEntity()` → `knowledgeActions.resolveTask`. Wizard-Komponente
  (`entity-wizard-dialog`) aus P23 direkt wiederverwendet, keine Kopie.
- [x] Store-Anbindung `store/persons/` (unverändert) + `store/knowledge/` (`loadDomains`,
  `loadTasks`, `resolveTask`, `dismissTask` — alle schon aus P23 vorhanden, nur neu konsumiert)
- [x] Doc: `docs/code-map.md`

## Deviations
- „Später" ist rein session-lokal (wie `work-queue.ts`s `snoozed`-Set) — kein Backend-Call,
  kein State-Feld auf dem Task. Beim nächsten Neuladen der Aufgabenliste taucht die Karte wieder auf.
  Bewusst identisch zum P23-Muster, nicht neu erfunden.
