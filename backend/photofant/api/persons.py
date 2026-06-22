"""Persons API — list, rename, merge and split Person records.

GET    /api/persons             → PersonDto[]
PATCH  /api/persons/{id}        → rename
POST   /api/persons/merge       → merge two persons
POST   /api/persons/{id}/split  → split faces into new person
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from photofant.db.models import AssetInstance, Face, Person
from photofant.db.session import get_session

log = logging.getLogger(__name__)

router = APIRouter(prefix="/persons")

DbSession = Annotated[Session, Depends(get_session)]


class PersonDto(BaseModel):
    id: int
    name: str | None
    is_unknown: bool
    count: int
    fav_count: int
    portrait_face_id: int | None


class CreatePersonRequest(BaseModel):
    name: str


class RenameRequest(BaseModel):
    name: str


class PersonFaceDto(BaseModel):
    id: int
    asset_id: int | None
    crop_url: str
    score: float | None
    age: int | None


class MergeRequest(BaseModel):
    from_id: int
    into_id: int


class SplitRequest(BaseModel):
    face_ids: list[int]


class MergeResultDto(BaseModel):
    faces_moved: int
    instances_moved: int


class SplitResultDto(BaseModel):
    new_person_id: int | None
    faces_moved: int
    instances_created: int


class PersonImportResponse(BaseModel):
    job_id: str


def _build_person_dto(session: Session, person: Person) -> PersonDto:
    count: int = (
        session.query(func.count(AssetInstance.id))
        .filter(
            AssetInstance.person_id == person.id,
            AssetInstance.deleted_at.is_(None),
        )
        .scalar()
    ) or 0

    fav_count: int = (
        session.query(func.count(AssetInstance.id))
        .filter(
            AssetInstance.person_id == person.id,
            AssetInstance.deleted_at.is_(None),
            AssetInstance.favourite.is_(True),
        )
        .scalar()
    ) or 0

    portrait_face: Face | None = (
        session.query(Face)
        .filter(Face.person_id == person.id)
        .order_by(Face.score.desc().nulls_last())
        .first()
    )

    return PersonDto(
        id=person.id,
        name=person.name,
        is_unknown=person.is_unknown,
        count=count,
        fav_count=fav_count,
        portrait_face_id=portrait_face.id if portrait_face is not None else None,
    )


@router.post("", response_model=PersonDto, status_code=201)
async def create_person(body: CreatePersonRequest, session: DbSession) -> PersonDto:
    """Create a new named person and ensure their folder exists."""
    from photofant.config import get_data_root
    from photofant.media.person_folders import ensure_person_folder

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name must not be empty")

    new_person = Person(name=name, is_unknown=False)
    session.add(new_person)
    session.flush()

    data_root = get_data_root()
    ensure_person_folder(data_root, new_person)

    session.commit()
    session.refresh(new_person)

    log.info("Created person %d with name %r", new_person.id, new_person.name)
    return _build_person_dto(session, new_person)


@router.get("", response_model=list[PersonDto])
async def list_persons(session: DbSession) -> list[PersonDto]:
    persons = (
        session.query(Person)
        .order_by(Person.is_unknown.asc(), Person.id.asc())
        .all()
    )
    return [_build_person_dto(session, person) for person in persons]


@router.get("/{person_id}/faces", response_model=list[PersonFaceDto])
async def list_person_faces(person_id: int, session: DbSession) -> list[PersonFaceDto]:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    faces = (
        session.query(Face)
        .filter(Face.person_id == person_id)
        .order_by(Face.id.asc())
        .all()
    )
    return [
        PersonFaceDto(
            id=face.id,
            asset_id=face.asset_id,
            crop_url=f"/faces/{face.id}/thumbnail",
            score=face.score,
            age=face.age,
        )
        for face in faces
    ]


@router.patch("/{person_id}", response_model=PersonDto)
async def rename_person(person_id: int, body: RenameRequest, session: DbSession) -> PersonDto:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    if person.is_unknown:
        raise HTTPException(status_code=400, detail="Cannot rename the unknown person")
    new_name = body.name.strip()
    if not new_name:
        raise HTTPException(status_code=422, detail="Name must not be empty")

    from photofant.config import get_data_root
    from photofant.media.person_folders import person_folder_name, rename_person_folder

    old_folder_name = person_folder_name(person)
    person.name = new_name
    session.flush()

    data_root = get_data_root()
    await asyncio.to_thread(rename_person_folder, session, person, old_folder_name, data_root)

    session.commit()
    session.refresh(person)
    log.info("Renamed person %d to %r", person_id, person.name)
    return _build_person_dto(session, person)


@router.post("/merge", response_model=MergeResultDto)
async def merge_persons_endpoint(body: MergeRequest, session: DbSession) -> MergeResultDto:
    """Merge from_person into into_person — all assets and faces move physically."""
    from photofant.config import get_data_root
    from photofant.media.person_folders import merge_persons

    from_person = session.get(Person, body.from_id)
    into_person = session.get(Person, body.into_id)
    if from_person is None:
        raise HTTPException(status_code=404, detail="Source person not found")
    if into_person is None:
        raise HTTPException(status_code=404, detail="Target person not found")
    if body.from_id == body.into_id:
        raise HTTPException(status_code=422, detail="Cannot merge a person into itself")

    data_root = get_data_root()

    try:
        result = await asyncio.to_thread(merge_persons, session, body.from_id, body.into_id, data_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session.commit()

    affected_assets = session.execute(
        select(AssetInstance.asset_id)
        .where(AssetInstance.person_id == body.into_id, AssetInstance.deleted_at.is_(None))
        .distinct()
    ).fetchall()
    asset_ids = [int(row[0]) for row in affected_assets]
    if asset_ids:
        from photofant.jobs.collections_job import enqueue_reevaluate_assets
        asyncio.ensure_future(enqueue_reevaluate_assets(asset_ids))

    return MergeResultDto(
        faces_moved=result["faces_moved"],
        instances_moved=result["instances_moved"],
    )


@router.post("/{person_id}/import", response_model=PersonImportResponse)
async def import_to_person_folder(
    person_id: int,
    session: DbSession,
    files: Annotated[list[UploadFile], File()],
) -> PersonImportResponse:
    """Upload images and import them into a person's photos/ folder with fixed_person=True."""
    from photofant.config import get_data_root
    from photofant.jobs.import_job import enqueue_person_import
    from photofant.media.person_folders import ensure_person_folder

    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    data_root = get_data_root()
    person_dir = ensure_person_folder(data_root, person)
    photos_dir = person_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for upload in files:
        filename = upload.filename or "upload.jpg"
        suffix = Path(filename).suffix.lower() or ".jpg"
        dest = photos_dir / filename
        counter = 1
        while dest.exists():
            stem = Path(filename).stem
            dest = photos_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        content = await upload.read()
        dest.write_bytes(content)
        saved_paths.append(str(dest))

    status = await enqueue_person_import(person_id, saved_paths)
    return PersonImportResponse(job_id=status.id)


@router.post("/{person_id}/split", response_model=SplitResultDto)
async def split_person(person_id: int, body: SplitRequest, session: DbSession) -> SplitResultDto:
    """Split selected faces from a person into a new person."""
    from photofant.config import get_data_root
    from photofant.media.person_folders import split_faces

    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    if not body.face_ids:
        raise HTTPException(status_code=422, detail="face_ids must not be empty")

    data_root = get_data_root()

    try:
        result = await asyncio.to_thread(split_faces, session, person_id, body.face_ids, data_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session.commit()
    return SplitResultDto(
        new_person_id=result["new_person_id"],
        faces_moved=result["faces_moved"],
        instances_created=result["instances_created"],
    )
