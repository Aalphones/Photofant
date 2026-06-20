"""Face API — thumbnails, matches, clustering, manual assignment, and direct import.

GET   /faces/{face_id}/thumbnail  → JPEG-Thumbnail (256 px) aus Cache-DB
GET   /faces/{face_id}/matches    → Top 10 disjunkte Personen (Cosine-Score)
POST  /faces/cluster              → Initial-Clustering (HDBSCAN) als Job
PATCH /faces/{face_id}/assign     → Manuelle Zuordnung zu einer Person (physischer Move)
POST  /faces/import               → Direkter Face-Import (Bild = Crop, origin=manual_original)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
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


class FaceImportResultDto(BaseModel):
    face_id: int
    person_id: int | None
    has_embedding: bool


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

        # pHash for the crop
        face_phash: str | None = None
        try:
            import imagehash
            from PIL import Image as PILImage
            img_ph = PILImage.open(dest).convert("RGB")
            face_phash = str(imagehash.dhash(img_ph, hash_size=8))
        except Exception:
            pass

        from photofant.db.models import Face as FaceModel

        face_row = FaceModel(
            asset_id=None,
            person_id=resolved_person_id,
            crop_path=str(dest.resolve()),
            embedding=embedding_bytes,
            phash=face_phash,
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
