# Phase 2 — Backend-API: DTO-Erweiterung + Bulk-Delete

**Rating:** standard (Kontrakt liegt fest in der README, reiner Verdrahtungs-Code).

**Voraussetzung:** Phase 1 abgeschlossen (`photofant.clustering.cleanup` existiert).

## Kontext (lesen vor dem Bauen)

- Kontrakt-Sektion in [README.md](README.md) — exakte Feldnamen/Typen der DTOs, nicht abweichen.
- `backend/photofant/api/persons.py`:
  - `PersonFaceDto` (Zeile ~85) und `list_person_faces` (Zeile ~266) — hier werden die neuen Felder
    additiv ergänzt. **Sortierung `order_by(Face.id.asc())` bleibt unverändert** (der bestehende
    `split-dialog` verlässt sich chronologisch darauf) — Sortierung nach `cleanup_score` passiert
    ausschließlich clientseitig im neuen Dialog (Phase 4).
- `backend/photofant/api/faces.py`:
  - `delete_face` (Zeile ~450) — bestehende Lösch-Logik, die für den Bulk-Endpoint in einen
    Helper extrahiert wird. **Verhalten für den Einzel-Endpoint darf sich nicht ändern.**
  - Modul-Docstring am Kopf der Datei (Zeile 1-9) listet die Routen — neue Route dort ergänzen.

## Aufgabe

### 1. `backend/photofant/api/persons.py` — `PersonFaceDto` erweitern

```python
class PersonFaceDto(BaseModel):
    id: int
    asset_id: int | None
    crop_url: str
    score: float | None
    age: int | None
    resolution: int | None = None
    is_upscaled: bool = False
    identity_distance: float | None = None
    cleanup_score: float = 0.0
    cleanup_reasons: list[str] = []
```

`list_person_faces` anpassen — Scores einmal pro Aufruf berechnen, dann pro Face nachschlagen:

```python
@router.get("/{person_id}/faces", response_model=list[PersonFaceDto])
async def list_person_faces(person_id: int, session: DbSession) -> list[PersonFaceDto]:
    from photofant.clustering.cleanup import compute_person_cleanup_scores

    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    faces = (
        session.query(Face)
        .filter(Face.person_id == person_id)
        .order_by(Face.id.asc())
        .all()
    )
    cleanup_by_face_id = {
        entry.face_id: entry for entry in compute_person_cleanup_scores(session, person_id)
    }
    return [
        PersonFaceDto(
            id=face.id,
            asset_id=face.asset_id,
            crop_url=f"/faces/{face.id}/thumbnail",
            score=face.score,
            age=face.age,
            resolution=face.resolution,
            is_upscaled=face.is_upscaled,
            identity_distance=(cleanup_by_face_id[face.id].identity_distance if face.id in cleanup_by_face_id else None),
            cleanup_score=(cleanup_by_face_id[face.id].cleanup_score if face.id in cleanup_by_face_id else 0.0),
            cleanup_reasons=(cleanup_by_face_id[face.id].reasons if face.id in cleanup_by_face_id else []),
        )
        for face in faces
    ]
```

(`compute_person_cleanup_scores` is imported lazily inside the function — same import style as the
rest of this file, e.g. `reassign_face` in `assign_face`, to avoid module-level import cycles.)

### 2. `backend/photofant/api/faces.py` — Helper extrahieren + Bulk-Endpoint

Modul-Docstring (Zeile 1-9) um die neue Route ergänzen:

```
POST  /faces/bulk-delete          → Mehrere Faces in einem Aufruf löschen (gebündelte Reevaluation)
```

Neuer privater Helper, direkt vor `delete_face` eingefügt:

```python
def _delete_face_row(session: Session, face: Face) -> int | None:
    """Delete one face's DB row + crop file + vector-index entry.

    Returns the face's asset_id (or None) so the caller can batch the
    downstream reconciliation (prune/invalidate/reevaluate) itself.
    Does NOT commit and does NOT run prune/invalidate/reevaluate — that's
    the caller's job, so a bulk delete can batch it across many faces.
    """
    from photofant.db.face_vector_index import delete_embedding

    asset_id = face.asset_id

    delete_embedding(session, face.id)

    crop_path = Path(face.crop_path)
    if crop_path.exists():
        try:
            crop_path.unlink()
        except OSError:
            log.warning("Could not delete crop file for face %d: %s", face.id, crop_path)

    session.delete(face)
    session.flush()

    return asset_id
```

`delete_face` darauf umstellen (Verhalten bleibt identisch — nur der Lösch-Kern ist jetzt der Helper):

```python
@router.delete("/{face_id}", status_code=204)
async def delete_face(face_id: int, session: DbSession) -> None:
    """Delete a face: removes DB row, crop file, and vector index entry.

    If the face belonged to an asset, smart-album re-evaluation is triggered.
    """
    face = session.get(Face, face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="Face not found")

    asset_id = _delete_face_row(session, face)

    if asset_id is not None:
        from photofant.config import get_data_root
        from photofant.media.person_folders import prune_orphaned_instances

        prune_orphaned_instances(session, asset_id, get_data_root())

        from photofant.jobs.recommendation_job import invalidate_recommendations

        invalidate_recommendations(session, [asset_id])

    session.commit()

    if asset_id is not None:
        from photofant.jobs.collections_job import enqueue_reevaluate_assets

        await enqueue_reevaluate_assets([asset_id])
```

Neue DTOs + Bulk-Endpoint, eingefügt nach `assign_face` (Datei-Ende):

```python
class BulkDeleteFacesRequest(BaseModel):
    face_ids: list[int]


class BulkDeleteFacesResultDto(BaseModel):
    deleted: int
    asset_ids: list[int]


@router.post("/bulk-delete", response_model=BulkDeleteFacesResultDto)
async def bulk_delete_faces(body: BulkDeleteFacesRequest, session: DbSession) -> BulkDeleteFacesResultDto:
    """Delete several faces in one call.

    Same per-face cleanup as DELETE /{face_id}, but batches smart-album
    re-evaluation + recommendation invalidation to one call per affected
    asset instead of one per deleted face — avoids N redundant job-dock
    entries when the cleanup dialog deletes many faces at once.
    Unknown face_ids are silently skipped (not counted in `deleted`).
    """
    if not body.face_ids:
        raise HTTPException(status_code=422, detail="face_ids darf nicht leer sein")

    affected_asset_ids: set[int] = set()
    deleted = 0

    for face_id in body.face_ids:
        face = session.get(Face, face_id)
        if face is None:
            continue
        asset_id = _delete_face_row(session, face)
        if asset_id is not None:
            affected_asset_ids.add(asset_id)
        deleted += 1

    if affected_asset_ids:
        from photofant.config import get_data_root
        from photofant.media.person_folders import prune_orphaned_instances

        data_root = get_data_root()
        for asset_id in affected_asset_ids:
            prune_orphaned_instances(session, asset_id, data_root)

    session.commit()

    if affected_asset_ids:
        from photofant.jobs.recommendation_job import invalidate_recommendations

        invalidate_recommendations(session, list(affected_asset_ids))

        from photofant.jobs.collections_job import enqueue_reevaluate_assets

        await enqueue_reevaluate_assets(list(affected_asset_ids))

    return BulkDeleteFacesResultDto(deleted=deleted, asset_ids=list(affected_asset_ids))
```

## Akzeptanzkriterien

- `GET /api/persons/{id}/faces` liefert die fünf neuen Felder für jede Face-Zeile, bestehende
  Felder unverändert, Reihenfolge unverändert (`id asc`).
- `POST /api/faces/bulk-delete` mit einer Liste bekannter `face_ids` löscht alle, gibt
  `{deleted, asset_ids}` zurück; mit einer leeren Liste → `422`; mit unbekannten IDs dazwischen →
  diese werden übersprungen, `deleted` zählt nur die tatsächlich gelöschten.
- `DELETE /faces/{id}` (Einzel-Endpoint) verhält sich exakt wie vorher — keine Regression
  (manueller Vergleich: Crop-Datei weg, `prune_orphaned_instances` läuft, Reevaluation wird
  ausgelöst, Response weiterhin `204`).

## Checkliste

- [x] `PersonFaceDto` + `list_person_faces` in `api/persons.py` erweitert
- [x] `_delete_face_row`-Helper in `api/faces.py`, `delete_face` darauf umgestellt
- [x] `POST /api/faces/bulk-delete` neu, Modul-Docstring aktualisiert
- [x] Manueller Smoke-Test: bestehenden Einzel-Face löschen funktioniert weiterhin identisch

## Report-Back

- Plan 1:1 umgesetzt, ein kleiner Stil-Fix nötig: die Feld-Zuweisungen für `identity_distance`/
  `cleanup_score`/`cleanup_reasons` in `list_person_faces` mussten auf mehrere Zeilen umgebrochen
  werden (`ruff` E501, Plan-Code-Snippet war 121 Zeichen in einer Zeile) — funktional identisch.
- `ruff check` auf beiden Dateien: sauber. `mypy`: 3 Fehler, alle drei bereits vor dieser Phase
  vorhanden (per `git stash`-Vergleich verifiziert) — nur Zeilennummer von `persons.py:203` auf
  `:208` verschoben, keine neuen Fehler.
- Bestandstests (`test_faces_api.py`, `test_recommendation_invalidation_manual.py`,
  `test_person_folders.py`, `test_knowledge_api.py`, 45 Tests) weiterhin grün — keine Regression
  am bestehenden `DELETE /faces/{id}`.
- Ad-hoc-Smoke-Skript (nicht Teil der Test-Suite) gegen eine Wegwerf-SQLite bestätigt:
  `GET /persons/{id}/faces` liefert die 5 neuen Felder korrekt befüllt (`low_resolution`/
  `upscaled`-Reasons greifen wie erwartet); `POST /faces/bulk-delete` mit leerer Liste → 422;
  mit zwei bekannten + einer unbekannten ID → `deleted: 2`, unbekannte übersprungen, `asset_ids`
  enthält das betroffene Asset genau **einmal** (beide gelöschten Faces hingen am selben Asset —
  Bündelung greift wie im Kontrakt gefordert).
- Keine Findings für Phase 3/4, keine Abweichungen vom Kontrakt.
