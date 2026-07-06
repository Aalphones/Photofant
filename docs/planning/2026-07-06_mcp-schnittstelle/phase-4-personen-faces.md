# Phase 4 — Personen & Faces

**Komplexität:** standard · **Status:** pending

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

- [ ] `tools/persons.py` registriert:
  - [ ] `create_person(name, group?)` → `POST /persons`.
  - [ ] `list_persons()` (falls nicht schon in Phase 2 ausreichend — sonst hier weglassen, kein Duplikat).
  - [ ] `rename_person(person_id, name?, group?)` → `PATCH /persons/{id}`.
  - [ ] `assign_person(person_id, asset_id? | face_id?)` → je nach Ziel `PATCH /assets/{id}/assign-person`
        **oder** `PATCH /faces/{id}/assign`. **Reversibel → kein Gate.**
  - [ ] `bulk_assign_person(person_id, asset_ids)` → `POST /persons/{id}/bulk-assign`.
  - [ ] `merge_persons(from_id, into_id, confirm=false)` → `POST /persons/merge`. **Gate.**
  - [ ] `split_person(person_id, face_ids)` → `POST /persons/{id}/split`.
  - [ ] `delete_person(person_id, confirm=false)` → `DELETE /persons/{id}`. **Gate.**
  - [ ] `list_faces(person_id?, page?)` → `GET /faces/gallery`.
  - [ ] `get_face_matches(face_id)` → `GET /faces/{id}/matches`.
  - [ ] `delete_face(face_id, confirm=false)` → `DELETE /faces/{id}`. **Gate.**
  - [ ] `recluster()` → `POST /faces/cluster` (async → `job_id`).
  - [ ] `list_face_review()` → `GET /review-queue`; `resolve_face_review(face_id, action, person_id?)`
        → `POST /review-queue/{face_id}` (confirm/reject/reassign). **Reversibel → kein Gate.**
- [ ] Gate-Tools verweigern ohne `confirm=true` und erklären die Folge (z. B. „Person X wird gelöscht,
      ihre Fotos wandern zu ‚Unbekannt'"). Bei `mcp.require_confirm=false` läuft es direkt.

## Umsetzung — Checkliste

- [ ] `tools/persons.py` mit den Tools oben; Gate-Tools über `gate.py`.
- [ ] `assign_person`-Verzweigung asset vs. face sauber dokumentieren (Docstring).
- [ ] Doc: `docs/routes.md` MCP-Abschnitt ergänzen.

## Report-Back
