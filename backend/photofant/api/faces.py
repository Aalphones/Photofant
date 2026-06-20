"""Face API — thumbnails, matches, clustering, and manual assignment.

GET   /faces/{face_id}/thumbnail  → JPEG-Thumbnail (256 px) aus Cache-DB
GET   /faces/{face_id}/matches    → Top 10 disjunkte Personen (Cosine-Score)
POST  /faces/cluster              → Initial-Clustering (HDBSCAN) als Job
PATCH /faces/{face_id}/assign     → Manuelle Zuordnung zu einer Person (physischer Move)
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.db.cache import get_cache_db_path, get_thumbnail, init_cache_db, store_thumbnail
from photofant.db.models import Face, Person
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
