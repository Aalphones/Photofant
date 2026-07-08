# Phase 1 — Task-Queue (Backend)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Kontrakt-Ergänzungen · **P22** (Service, `find_entity`, Cache)
- Bestand: `db/models.py`+`alembic/`, `api/`-Muster, `jobs/queue.py`, `jobs/*_job.py`, `docs/models.md`, `docs/routes.md`

## AK
- [x] Migration `knowledge_tasks` (Felder laut Kontrakt); up/down grün.
- [x] REST: anlegen, nach `status` auflisten, auflösen, verwerfen — je korrekter Statuswechsel.
- [x] `KnowledgeLookupJob` prüft via `find_entity`; fehlt sie, genau eine Aufgabe; zweiter Lauf zum selben `context` → kein Duplikat.
- [x] Job läuft über die bestehende Queue.

## Umsetzung
- [x] `db/models.py` + Migration (`0035_knowledge_tasks.py`)
- [x] `knowledge/tasks.py` — TaskService (CRUD + Dedup über `context`)
- [x] Task-Routen in eigenem `api/knowledge_tasks.py` (getrennt von `api/knowledge.py`, konsistent zu den anderen Domain-Routern wie `maintenance.py`) + `POST /lookup`-Trigger
- [x] `jobs/knowledge_lookup_job.py` + Registrierung (`main.py`, `JobKind.KNOWLEDGE_LOOKUP`)
- [x] Doc: `docs/models.md`, `docs/routes.md`, `docs/code-map.md`
- [x] Tests: `test_knowledge_tasks.py` (Service), `test_knowledge_tasks_api.py` (REST), `test_knowledge_lookup_job.py` (Job)

## Abweichungen vom Plan
- Task-Routen in eigenem `api/knowledge_tasks.py` statt in `api/knowledge.py` — sauberere Trennung
  (Aufgaben sind Arbeitszustand, keine Entity-Mutation), Plan hatte beides zur Wahl gestellt.
- `resolved_at` wird sowohl bei `resolve` als auch bei `dismiss` gesetzt (ein Feld „wann
  geschlossen" statt zwei) — Kontrakt nannte nur ein Timestamp-Feld, dismiss braucht aber auch
  einen Abschlusszeitpunkt.
- Zusätzlicher `POST /api/knowledge/lookup`-Endpoint (nicht im Kontrakt gelistet, aber laut
  README-Scope „hier manuell auslösbar" nötig, sonst kein Weg den Job ohne P24-Trigger anzustoßen).
