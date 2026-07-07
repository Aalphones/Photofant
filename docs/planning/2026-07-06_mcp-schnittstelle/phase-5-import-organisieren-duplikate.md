# Phase 5 — Import, Organisieren, Duplikate

**Komplexität:** standard · **Status:** complete

## Kontext (vor dem Bauen lesen)

- `README.md` — Kontrakt, Gate (hier: `empty_trash`, `resolve_duplicate` bei `delete_*`), Job-Regel.
- `phase-1` — `gate.py`, `adapter.py`.
- `backend/photofant/api/assets.py` — `import` (`POST /assets/import`, Serverpfade), `scan`
  (`POST /assets/scan`), `favourite` (`PATCH /assets/{id}/favourite`), `trash` (`DELETE /assets/{id}`),
  `bulk-trash` (`POST /assets/bulk-trash`). **Browser-Upload (`/upload`) ist kein MCP-Tool** (kein
  Datei-Handle im Agent-Kontext) — nur `import` per Serverpfad.
- `backend/photofant/api/classify.py` — `run_processing` (`POST /classify/rerun`, Steps
  tags/caption/embedding/faces/heuristics/categories).
- `backend/photofant/api/trash.py` — `list_trash`, `restore` (`POST /trash/{id}/restore`),
  `empty_trash` (`DELETE /trash`), `delete_forever` (`DELETE /trash/{id}`).
- `backend/photofant/api/collections.py` — Alben/Smart-Alben/Trainingssets CRUD + Trigger + Items +
  Stats + Caption-Tools + `duplicates`/`resolve`.
- `backend/photofant/api/review.py` — `list_duplicates` (`GET /review/dupes`), `resolve_duplicate`
  (`PATCH /review/dupes/{id}`).
- `backend/photofant/api/jobs.py` — `scan_duplicates` (`POST /jobs/dupe-scan`).
- `backend/photofant/api/duplicates.py` — `find_person_duplicates` (`POST /duplicates/search`).
- `docs/routes.md` — Abschnitte „Collections", „Export", „Duplikaterkennung", „Papierkorb".

## AK (falsifizierbar)

- [x] `tools/organize.py` registriert:
  - **Import & Verarbeitung**
    - [x] `import_paths(paths)` → `POST /assets/import` (async → `job_id`).
    - [x] `scan_library()` → `POST /assets/scan` (async → `job_id`).
    - [x] `run_processing(asset_ids | "all", steps, caption_preset_id?)` → `POST /classify/rerun`
          (async → `job_id`). Steps: tags/caption/embedding/faces/heuristics/categories.
  - **Papierkorb & Favoriten**
    - [x] `favourite_photo(asset_id, value)` → `PATCH /assets/{id}/favourite`. Kein Gate.
    - [x] `trash_photo(asset_id)` / `bulk_trash(asset_ids)` → Soft-Delete. **Reversibel → kein Gate.**
    - [x] `restore_photo(asset_id)` → `POST /trash/{id}/restore`.
    - [x] `list_trash()` → `GET /trash`.
    - [x] `empty_trash(confirm=false)` → `DELETE /trash`. **Gate.**
  - **Alben & Trainingssets**
    - [x] `list_collections()` / `create_collection(name, kind?, match_mode?)` /
          `update_collection(id, ...)` / `delete_collection(id, confirm=false)` **Gate** →
          `/collections`-CRUD.
    - [x] `add_to_collection(collection_id, asset_ids)` / `remove_from_collection(collection_id, asset_id)`.
    - [x] `manage_collection_triggers(collection_id, ...)` → Trigger-CRUD (Smart-Alben).
    - [x] `training_set_stats(collection_id)` → `GET /collections/{id}/stats`.
    - [x] `training_set_captions(collection_id, action, params)` → `POST /collections/{id}/captions`
          (async → `job_id`).
    - [x] `export_collection(collection_id, sidecar?, split_ratio?, target_dir?)` →
          `POST /collections/{id}/export` (async → `job_id`).
  - **Duplikate**
    - [x] `scan_duplicates(scope, asset_ids?)` → `POST /jobs/dupe-scan` (async → `job_id`).
    - [x] `list_duplicates(offset?, limit?)` → `GET /review/dupes`.
    - [x] `resolve_duplicate(pair_id, resolution)` → `PATCH /review/dupes/{id}`. **Gate nur bei
          `delete_a`/`delete_b`** (`a_is_original`/`b_is_original`/`dismiss` sind reversibel → kein Gate).
    - [x] `find_person_duplicates(person_id, clip_threshold?)` → `POST /duplicates/search`.

## Umsetzung — Checkliste

- [x] `tools/organize.py` mit den Tools oben; Gate-Tools über `gate.py`.
- [x] `resolve_duplicate`: Gate **bedingt** an der `resolution` (nur `delete_*`).
- [x] Doc: `docs/routes.md` MCP-Abschnitt ergänzen.

## Report-Back

23 Write-Tools in `mcp/tools/organize.py`: Import/Scan/Processing (3), Papierkorb/Favoriten (5,
davon `empty_trash` mit Gate), Alben/Trainingssets (9, davon `delete_collection` mit Gate),
Duplikate (4, davon `resolve_duplicate` mit bedingtem Gate nur bei `delete_a`/`delete_b`).
`run_processing` und `scan_duplicates` rufen ihren Endpoint (`trigger_rerun`/`start_dupe_scan`)
**direkt** auf statt über `run_endpoint()` — beide brauchen keine DB-Session (öffnen sie selbst
im Job), `run_endpoint()` würde mit einem unerwarteten `session`-Kwarg scheitern (gleiches Muster
wie `set_classification` in Phase 3, FINDINGS.md-Eintrag „Phase 3/4/5/6: sync/session-lose
Endpoints"). `list_trash`/`list_collections`/Trigger-`list` haben keine Pagination im Endpoint —
hier clientseitig auf `mcp.max_search_results` gedeckelt, `total` zählt die volle Menge.
`manage_collection_triggers` bündelt list/create/update/delete in einem Tool (so im Plan
vorgesehen). ruff/mypy grün, alle 56 Tools registrieren fehlerfrei (33 aus Phase 1-4 + 23 neu).
`docs/routes.md` MCP-Tabelle ergänzt. Kein Live-Smoke in dieser Phase (private-Profil: Smoke
einmal am Plan-Ende, durch den User).
