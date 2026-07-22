"""Face API — thumbnails, matches, clustering, manual assignment, and direct import.

GET   /faces/gallery              → Paginated face-crop gallery
GET   /faces/{face_id}/thumbnail  → JPEG-Thumbnail (256 px) aus Cache-DB
GET   /faces/{face_id}/matches    → Top 10 disjunkte Personen (Cosine-Score)
POST  /faces/cluster              → Initial-Clustering (HDBSCAN) als Job
PATCH /faces/{face_id}/assign     → Manuelle Zuordnung zu einer Person (physischer Move)
POST  /faces/import               → Direkter Face-Import (Bild = Crop, origin=manual_original)
POST  /faces/bulk-delete          → Mehrere Faces in einem Aufruf löschen (gebündelte Reevaluation)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from photofant.api.assets import ResDto, VersionDto
from photofant.db.cache import get_cache_db_path, get_thumbnail, init_cache_db, store_thumbnail
from photofant.db.models import Face, Person, Version
from photofant.db.session import get_session
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)

router = APIRouter(prefix="/faces")

DbSession = Annotated[Session, Depends(get_session)]


class FaceMatchDto(BaseModel):
    person_id: int
    person_name: str | None
    best_face_id: int
    score: float


class ClusterResultDto(BaseModel):
    job_id: str


class AssignRequest(BaseModel):
    person_id: int


class AssignResultDto(BaseModel):
    face_id: int
    old_person_id: int | None
    new_person_id: int
    asset_id: int | None


class FaceImportResultDto(BaseModel):
    face_id: int
    person_id: int | None
    has_embedding: bool


class FaceGalleryItemDto(BaseModel):
    id: int
    asset_id: int | None
    person_id: int | None
    person_name: str | None
    thumbnail_url: str
    score: float | None
    age: int | None
    is_upscaled: bool
    origin: str | None
    created_at: datetime | None
    # P21 — Stapel (Face + eigene Editor-Dialog-Versionen, gruppiert über version.face_id):
    kind: str = "face"  # "face" | "version"
    version_id: int | None = None
    stack_size: int = 1
    stack_group_id: int | None = None


class FacesGalleryPage(BaseModel):
    items: list[FaceGalleryItemDto]
    total: int
    page: int
    page_size: int


class FaceDetailDto(BaseModel):
    id: int
    person_id: int | None
    person_name: str | None
    crop_url: str
    score: float | None
    age: int | None
    source_asset_id: int | None
    versions: list[VersionDto]
    created_at: datetime | None


@dataclass
class _FaceGalleryEntry:
    """One row of the merged Gesichter-Galerie result — a Face or a Version-Pseudo-Eintrag."""

    face: Face
    version: Version | None = None
    sort_key: Any = None


@router.get("/gallery", response_model=FacesGalleryPage)
async def list_faces_gallery(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 50,
    person_id: int | None = None,
    asset_ids: Annotated[list[int] | None, Query()] = None,
) -> FacesGalleryPage:
    query = session.query(Face)
    if person_id is not None:
        query = query.filter(Face.person_id == person_id)
    if asset_ids:
        query = query.filter(Face.asset_id.in_(asset_ids))

    # P21 — Version-Pseudo-Einträge (Face-Edits) für Faces, die die obigen Filter passieren.
    face_ids_sub = query.with_entities(Face.id).scalar_subquery()
    version_query = (
        session.query(Version, Face)
        .join(Face, Face.id == Version.face_id)
        .filter(Version.face_id.in_(face_ids_sub))
    )

    total = query.count() + version_query.count()

    # Merge-Strategie wie bei list_assets: Top `fetch_limit` je Teilstream reicht,
    # kein Full-Table-Fetch nötig.
    fetch_limit = page * page_size
    face_rows = query.order_by(Face.created_at.desc()).limit(fetch_limit).all()
    version_rows = version_query.order_by(Version.created_at.desc()).limit(fetch_limit).all()

    entries: list[_FaceGalleryEntry] = [
        _FaceGalleryEntry(face=face, sort_key=face.created_at) for face in face_rows
    ] + [
        _FaceGalleryEntry(face=face, version=version, sort_key=version.created_at)
        for version, face in version_rows
    ]
    entries.sort(key=lambda entry: (entry.sort_key is None, entry.sort_key), reverse=True)
    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]

    face_ids_on_page = {entry.face.id for entry in page_entries}
    version_counts_by_face: dict[int, int] = {}
    if face_ids_on_page:
        version_counts_by_face = {
            int(face_id): int(count)
            for face_id, count in (
                session.query(Version.face_id, func.count(Version.id))
                .filter(Version.face_id.in_(face_ids_on_page))
                .group_by(Version.face_id)
                .all()
            )
        }

    person_ids = {entry.face.person_id for entry in page_entries if entry.face.person_id is not None}
    person_names: dict[int, str] = {}
    if person_ids:
        persons = session.query(Person).filter(Person.id.in_(person_ids)).all()
        person_names = {p.id: p.name for p in persons if p.name is not None}

    items: list[FaceGalleryItemDto] = []
    for entry in page_entries:
        face = entry.face
        stack_size = 1 + version_counts_by_face.get(face.id, 0)
        stack_group_id = face.id if stack_size > 1 else None
        person_name = person_names.get(face.person_id) if face.person_id is not None else None

        if entry.version is None:
            items.append(FaceGalleryItemDto(
                id=face.id,
                asset_id=face.asset_id,
                person_id=face.person_id,
                person_name=person_name,
                thumbnail_url=f"/api/faces/{face.id}/thumbnail",
                score=face.score,
                age=face.age,
                is_upscaled=face.is_upscaled,
                origin=face.origin,
                created_at=face.created_at,
                stack_size=stack_size,
                stack_group_id=stack_group_id,
            ))
        else:
            version = entry.version
            items.append(FaceGalleryItemDto(
                id=face.id,
                asset_id=face.asset_id,
                person_id=face.person_id,
                person_name=person_name,
                thumbnail_url=f"/api/versions/{version.id}/thumbnail",
                score=face.score,
                age=face.age,
                is_upscaled=face.is_upscaled,
                origin=face.origin,
                created_at=version.created_at,
                kind="version",
                version_id=version.id,
                stack_size=stack_size,
                stack_group_id=stack_group_id,
            ))

    return FacesGalleryPage(items=items, total=total, page=page, page_size=page_size)


def _load_face_versions(session: Session, face_id: int) -> list[VersionDto]:
    versions = (
        session.query(Version)
        .filter(Version.face_id == face_id)
        .order_by(Version.created_at.asc())
        .all()
    )
    result: list[VersionDto] = []
    for version in versions:
        params = version.params or {}
        width = params.get("width")
        height = params.get("height")
        res = ResDto(width=width, height=height) if width and height else None
        result.append(VersionDto(
            id=version.id,
            type=version.type,
            parent_id=version.parent_id,
            path=version.path,
            is_current=version.is_current,
            params=version.params,
            created_at=version.created_at,
            res=res,
            thumbnail_url=f"/api/versions/{version.id}/thumbnail",
        ))
    return result


@router.get("/{face_id}", response_model=FaceDetailDto)
async def get_face(face_id: int, session: DbSession) -> FaceDetailDto:
    """Face detail for the Gesichter-Modus of the Lightbox: own versions + source-asset link."""
    face = session.get(Face, face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="Face not found")

    person_name: str | None = None
    if face.person_id is not None:
        person = session.get(Person, face.person_id)
        person_name = person.name if person else None

    return FaceDetailDto(
        id=face.id,
        person_id=face.person_id,
        person_name=person_name,
        crop_url=f"/faces/{face.id}/thumbnail",
        score=face.score,
        age=face.age,
        source_asset_id=face.asset_id,
        versions=_load_face_versions(session, face_id),
        created_at=face.created_at,
    )


@router.get("/{face_id}/thumbnail")
async def get_face_thumbnail(
    face_id: int,
    session: DbSession,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
) -> Response:
    face = session.get(Face, face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="Face not found")

    etag = f'"{face_id}-256"'
    if if_none_match == etag:
        return Response(status_code=304)

    db_path = get_cache_db_path()
    init_cache_db(db_path)
    data = await asyncio.to_thread(get_thumbnail, db_path, face_id, 256, "face")

    if data is None:
        crop_path = Path(face.crop_path)
        if not crop_path.exists():
            raise HTTPException(status_code=404, detail="Face crop file not found")
        data = await asyncio.to_thread(generate_thumbnail, crop_path, 256)
        await asyncio.to_thread(store_thumbnail, db_path, face_id, 256, data, "face")

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "max-age=86400",
            "ETag": etag,
        },
    )


@router.get("/{face_id}/matches")
async def get_face_matches(face_id: int, session: DbSession) -> list[FaceMatchDto]:
    """Top 10 disjoint persons matched by cosine similarity."""
    from photofant.db.face_vector_index import search_disjoint_persons

    face = session.get(Face, face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="Face not found")
    if face.embedding is None:
        raise HTTPException(status_code=409, detail={"code": "NO_EMBEDDING"})

    embedding = np.frombuffer(face.embedding, dtype=np.float32).copy()

    matches = await asyncio.to_thread(
        search_disjoint_persons, session, embedding, exclude_face_id=face_id, limit=10,
    )

    unknown_person = session.query(Person).filter_by(is_unknown=True).first()
    unknown_person_id = unknown_person.id if unknown_person else None

    results: list[FaceMatchDto] = []
    for match in matches:
        person_id = int(match["person_id"])
        if person_id == unknown_person_id:
            continue
        person = session.get(Person, person_id)
        results.append(FaceMatchDto(
            person_id=person_id,
            person_name=person.name if person else None,
            best_face_id=int(match["best_face_id"]),
            score=float(match["score"]),
        ))

    return results


@router.post("/import", response_model=list[FaceImportResultDto])
async def import_faces_direct(
    session: DbSession,
    person_id: Annotated[int | None, Form()] = None,
    files: Annotated[list[UploadFile], File()] = None,  # type: ignore[assignment]
) -> list[FaceImportResultDto]:
    """Import face images directly: each image IS the face crop (origin=manual_original).

    No detection is run. The ArcFace model computes an embedding from the full
    image (resized to 112×112). The face is matchable but has no associated asset.
    """
    from photofant.config import get_data_root
    from photofant.db.models import Person
    from photofant.inference.adapters.buffalo_l import resolve_buffalo_l
    from photofant.media.person_folders import ensure_person_folder

    if not files:  # None or empty list
        raise HTTPException(status_code=422, detail="No files provided")

    engine = resolve_buffalo_l()

    data_root = get_data_root()

    resolved_person_id: int | None = None
    if person_id is not None:
        person = session.get(Person, person_id)
        if person is None:
            raise HTTPException(status_code=404, detail="Person not found")
        person_dir = ensure_person_folder(data_root, person)
        faces_dir = person_dir / "faces"
        resolved_person_id = person_id
    else:
        unknown = session.query(Person).filter_by(is_unknown=True).first()
        faces_dir = data_root / "_unknown" / "faces"
        resolved_person_id = unknown.id if unknown else None

    faces_dir.mkdir(parents=True, exist_ok=True)

    results: list[FaceImportResultDto] = []

    for upload in files:
        filename = upload.filename or "face.jpg"
        suffix = Path(filename).suffix.lower() or ".jpg"
        dest = faces_dir / filename
        counter = 1
        while dest.exists():
            stem = Path(filename).stem
            dest = faces_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        content = await upload.read()
        dest.write_bytes(content)

        embedding_bytes: bytes | None = None
        if engine is not None:
            try:
                from PIL import Image as PILImage
                img_pil = PILImage.open(dest).convert("RGB")
                img_np = np.array(img_pil, dtype=np.uint8)
                emb = await asyncio.to_thread(engine.embed_crop, img_np)
                if emb is not None:
                    embedding_bytes = emb.astype(np.float32).tobytes()
            except Exception:
                log.exception("embed_crop failed for %s", dest.name)

        from photofant.db.models import Face as FaceModel

        face_row = FaceModel(
            asset_id=None,
            person_id=resolved_person_id,
            crop_path=str(dest.resolve()),
            embedding=embedding_bytes,
            origin="manual_original",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        session.add(face_row)
        session.flush()
        face_id = face_row.id
        session.commit()

        # Thumbnail + vector index
        try:
            from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
            from photofant.media.thumbnails import generate_thumbnail
            thumb_data = await asyncio.to_thread(generate_thumbnail, dest, 256)
            db_path = get_cache_db_path()
            init_cache_db(db_path)
            await asyncio.to_thread(store_thumbnail, db_path, face_id, 256, thumb_data, "face")
        except Exception:
            log.exception("Thumbnail failed for imported face %d", face_id)

        if embedding_bytes is not None:
            try:
                from photofant.db.face_vector_index import upsert_embedding
                from photofant.db.session import SessionLocal
                emb_np = np.frombuffer(embedding_bytes, dtype=np.float32).copy()
                with SessionLocal() as vec_session:
                    upsert_embedding(vec_session, face_id, emb_np)
                    vec_session.commit()
            except Exception:
                log.exception("Vector index upsert failed for imported face %d", face_id)

        results.append(FaceImportResultDto(
            face_id=face_id,
            person_id=resolved_person_id,
            has_embedding=embedding_bytes is not None,
        ))

    return results


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


@router.delete("/{face_id}", status_code=204)
async def delete_face(face_id: int, session: DbSession) -> None:
    """Delete a face: removes DB row, crop file, and vector index entry.

    If the face belonged to an asset, smart-album re-evaluation is triggered.
    """
    face = session.get(Face, face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="Face not found")

    asset_id = _delete_face_row(session, face)

    # Prune every instance this asset no longer has a face for. The deleted
    # face's person may differ from the instance that's now orphaned (e.g. an
    # import-into-person assignment whose face never matched that person).
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


@router.post("/cluster")
async def trigger_clustering() -> ClusterResultDto:
    """Trigger initial HDBSCAN clustering over all face embeddings."""
    from photofant.jobs.clustering_job import enqueue_clustering

    status = await enqueue_clustering()
    return ClusterResultDto(job_id=status.id)


@router.patch("/{face_id}/assign")
async def assign_face(
    face_id: int,
    body: AssignRequest,
    session: DbSession,
) -> AssignResultDto:
    """Manually reassign a face to a different person.

    Moves the image file + face crop to the target person's folder,
    sets fixed_person on the instance, and fires smart-album re-evaluation.
    """
    from photofant.config import get_data_root
    from photofant.media.person_folders import reassign_face

    face = session.get(Face, face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="Face not found")

    target = session.get(Person, body.person_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target person not found")

    data_root = get_data_root()

    try:
        result = await asyncio.to_thread(
            reassign_face, session, face_id, body.person_id, data_root,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if result["asset_id"] is not None:
        from photofant.jobs.recommendation_job import invalidate_recommendations

        invalidate_recommendations(session, [result["asset_id"]])

    session.commit()

    if result["asset_id"] is not None:
        from photofant.jobs.collections_job import enqueue_reevaluate_assets

        await enqueue_reevaluate_assets([result["asset_id"]])

    return AssignResultDto(
        face_id=result["face_id"],
        old_person_id=result["old_person_id"],
        new_person_id=result["new_person_id"],
        asset_id=result["asset_id"],
    )


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
