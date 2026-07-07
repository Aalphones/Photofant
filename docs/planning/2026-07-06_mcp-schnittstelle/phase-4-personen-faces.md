# Phase 4 — Personen & Faces

**Komplexität:** standard · **Status:** complete

## Kontext (vor dem Bauen lesen)

- `README.md` — Kontrakt, **Confirmation-Gate** (hier erstmals genutzt: `delete_person`, `merge_persons`,
  `delete_face`).
- `phase-1` — `gate.py:confirmation_required()`.
- `backend/photofant/api/persons.py` — `create_person` (`POST /persons`), `list_persons`,
  `rename`/`set_group` (`PATCH /persons/{id}`), `merge` (`POST /persons/merge`), `split`
  (`POST /persons/{id}/split`), `delete` (`DELETE /persons/{id}`), `bulk_assign`
  (`POST /persons/{id}/bulk-assign`), `import` (`POST /persons/{id}/import`), `faces`
  (`GET /persons/{id}/faces`).
- `backend/photofant/api/faces.py` — `list_faces` (`GET /faces/gallery`), `get_face` (`GET /faces/{id}`),
  `get_face_matches` (`GET /faces/{id}/matches`), `assign` (`PATCH /faces/{id}/assign`), `delete_face`
  (`DELETE /faces/{id}`), `cluster` (`POST /faces/cluster`).
- `backend/photofant/api/assets.py` — `assign_person` ohne Gesicht (`PATCH /assets/{id}/assign-person`).
- `backend/photofant/api/review_queue.py` — Face-Review-Queue (`GET /review-queue`, `POST /review-queue/{face_id}`).
- `docs/routes.md` — Abschnitte „Personen", „Faces", „Review-Queue — Gesichter", „Merge & Split".

## AK (falsifizierbar)

- [x] `tools/persons.py` registriert:
  - [x] `create_person(name, group?)` → `POST /persons`.
  - [x] `list_persons()` — steht bereits aus Phase 2 in `tools/library.py`, kein Duplikat.
  - [x] `rename_person(person_id, name?, group?)` → `PATCH /persons/{id}`.
  - [x] `assign_person(person_id, asset_id? | face_id?)` → je nach Ziel `PATCH /assets/{id}/assign-person`
        **oder** `PATCH /faces/{id}/assign`. **Reversibel → kein Gate.**
  - [x] `bulk_assign_person(person_id, asset_ids)` → `POST /persons/{id}/bulk-assign`.
  - [x] `merge_persons(from_id, into_id, confirm=false)` → `POST /persons/merge`. **Gate.**
  - [x] `split_person(person_id, face_ids)` → `POST /persons/{id}/split`.
  - [x] `delete_person(person_id, confirm=false)` → `DELETE /persons/{id}`. **Gate.**
  - [x] `list_faces(person_id?, page?)` → `GET /faces/gallery`.
  - [x] `get_face_matches(face_id)` → `GET /faces/{id}/matches`.
  - [x] `delete_face(face_id, confirm=false)` → `DELETE /faces/{id}`. **Gate.**
  - [x] `recluster()` → `POST /faces/cluster` (async → `job_id`).
  - [x] `list_face_review()` → `GET /review-queue`; `resolve_face_review(face_id, action, person_id?)`
        → `POST /review-queue/{face_id}` (confirm/reject/reassign). **Reversibel → kein Gate.**
- [x] Gate-Tools verweigern ohne `confirm=true` und erklären die Folge (z. B. „Person X wird gelöscht,
      ihre Fotos wandern zu ‚Unbekannt'"). Bei `mcp.require_confirm=false` läuft es direkt.

## Umsetzung — Checkliste

- [x] `tools/persons.py` mit den Tools oben; Gate-Tools über `gate.py`.
- [x] `assign_person`-Verzweigung asset vs. face sauber dokumentiert (Docstring).
- [x] Doc: `docs/routes.md` MCP-Abschnitt ergänzt.

## Report-Back

13 Tools in `backend/photofant/mcp/tools/persons.py`. `create_person` ruft bei gesetztem `group`
zusätzlich `update_person` (Endpoint kennt `group_name` nicht beim Anlegen). `resolve_face_review`
gibt `dict[str, str]` vom Endpoint zurück — für den `dict[str, object]`-Vertrag per `dict(result)`
umkopiert (mypy: dict ist invariant). `ruff`/`mypy` grün, alle 13 Tools registrieren sauber
(`mcp_server.list_tools()` geprüft — 33 Tools insgesamt, keine Schema-Fehler).
