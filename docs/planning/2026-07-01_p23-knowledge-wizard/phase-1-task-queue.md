# Phase 1 — Task-Queue (Backend)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Kontrakt-Ergänzungen · **P22** (Service, `find_entity`, Cache)
- Bestand: `db/models.py`+`alembic/`, `api/`-Muster, `jobs/queue.py`, `jobs/*_job.py`, `docs/models.md`, `docs/routes.md`

## AK
- [ ] Migration `knowledge_tasks` (Felder laut Kontrakt); up/down grün.
- [ ] REST: anlegen, nach `status` auflisten, auflösen, verwerfen — je korrekter Statuswechsel.
- [ ] `KnowledgeLookupJob` prüft via `find_entity`; fehlt sie, genau eine Aufgabe; zweiter Lauf zum selben `context` → kein Duplikat.
- [ ] Job läuft über die bestehende Queue.

## Umsetzung
- [ ] `db/models.py` + Migration
- [ ] `knowledge/tasks.py` — TaskService (CRUD + Dedup über `context`)
- [ ] Task-Routen in `api/knowledge.py` (oder `api/knowledge_tasks.py`, konsistent zu P22)
- [ ] `jobs/knowledge_lookup_job.py` + Registrierung
- [ ] Doc: `docs/models.md`, `docs/routes.md`, `docs/code-map.md`
