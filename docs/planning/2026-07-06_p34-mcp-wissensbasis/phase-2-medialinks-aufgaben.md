# Phase 2 — Media-Links + Wissens-Aufgaben

**Komplexität:** standard · **Unterbau:** P23, P24 · **Status:** pending

## Kontext (vor dem Bauen lesen)

- `README.md` + `phase-1` — Owner-Semantik, etabliertes Tool-Muster in `mcp/tools/knowledge.py`.
- `2026-07-01_p24-photofant-integration/README.md` — Kontrakt: `POST/DELETE /api/persons/{id}/link-entity`,
  `/api/assets/{id}/link-entity`, `linked_entity`-DTO.
- `2026-07-01_p23-knowledge-wizard/README.md` — Kontrakt: `knowledge_tasks`, REST
  `GET /api/knowledge/tasks?status=`, `POST .../tasks`, `.../tasks/{id}/resolve`, `.../dismiss`.
- Beim Umsetzen: realer `api/persons.py`/`api/assets.py` (link-entity) + `api/knowledge.py` (tasks).

## AK (falsifizierbar)

- [ ] In `mcp/tools/knowledge.py` ergänzt:
  - **Media-Links**
    - [ ] `link_entity(entity_id, person_id? | asset_id?)` → je nach Ziel
          `POST /api/persons/{id}/link-entity` **oder** `POST /api/assets/{id}/link-entity`.
    - [ ] `unlink_entity(entity_id, person_id? | asset_id?, confirm=false)` → analog `DELETE`. **Gate.**
    - [ ] `get_linked_entity(person_id? | asset_id?)` → aktuelle Verknüpfung (id, title, type) read-only.
  - **Aufgaben-Queue**
    - [ ] `list_knowledge_tasks(status?)` → `GET /api/knowledge/tasks` (open/resolved/dismissed).
    - [ ] `create_knowledge_task(kind, context)` → `POST /api/knowledge/tasks` (idempotent über `context`,
          Endpoint-Logik aus P23).
    - [ ] `resolve_knowledge_task(task_id)` → `POST .../tasks/{id}/resolve`.
    - [ ] `dismiss_knowledge_task(task_id)` → `POST .../tasks/{id}/dismiss`.
- [ ] `link_entity`/`unlink_entity` dokumentieren die Person-vs-Asset-Verzweigung in der Description.
- [ ] Verknüpfen ist reversibel → kein Gate; nur `unlink_entity` hat das Gate.

## Umsetzung — Checkliste

- [ ] Media-Link- + Task-Tools in `mcp/tools/knowledge.py`.
- [ ] Doc: `docs/routes.md` MCP-Wissens-Abschnitt ergänzen.

## Report-Back
