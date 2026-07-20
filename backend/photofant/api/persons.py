"""Persons API — list, rename, merge and split Person records.

GET    /api/persons                 → PersonDto[]
PATCH  /api/persons/{id}            → rename
POST   /api/persons/merge           → merge two persons
POST   /api/persons/{id}/split      → split faces into new person
POST   /api/persons/{id}/link-entity   → mit Wissens-Entity verknüpfen (P24)
DELETE /api/persons/{id}/link-entity   → Verknüpfung lösen (P24)
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from photofant.db.models import AssetInstance, Face, Person
from photofant.db.session import get_session
from photofant.knowledge.schema import Owner
from photofant.knowledge.service import EntityNotFoundError, KnowledgeService, OwnershipConflictError
from photofant.knowledge.vault import Vault, open_vault

log = logging.getLogger(__name__)

router = APIRouter(prefix="/persons")

DbSession = Annotated[Session, Depends(get_session)]
VaultDep = Annotated[Vault, Depends(open_vault)]


def _parse_owner(value: str) -> Owner:
    try:
        return Owner(value)
    except ValueError as error:
        allowed = ", ".join(owner.value for owner in Owner)
        raise HTTPException(
            status_code=422, detail=f"Unbekannter Owner '{value}' (erlaubt: {allowed})"
        ) from error


class EntityRefDto(BaseModel):
    id: str
    title: str
    type: str


class PersonDto(BaseModel):
    id: int
    name: str | None
    is_unknown: bool
    count: int
    fav_count: int
    portrait_face_id: int | None
    group_name: str | None
    created_at: datetime | None
    linked_entity: EntityRefDto | None = None


class LinkEntityRequest(BaseModel):
    entity_id: str
    owner: str = Owner.USER.value


class CreatePersonRequest(BaseModel):
    name: str


class UpdatePersonRequest(BaseModel):
    name: str | None = None
    group_name: str | None = None


class PersonFaceDto(BaseModel):
    id: int
    asset_id: int | None
    crop_url: str
    score: float | None
    age: int | None


class MergeRequest(BaseModel):
    from_id: int
    into_id: int


class BulkAssignRequest(BaseModel):
    asset_ids: list[int]


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


def _build_person_dto(session: Session, person: Person, vault: Vault) -> PersonDto:
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

    linked_entity = KnowledgeService(session, vault).linked_entity_ref("person", person.id)

    return PersonDto(
        id=person.id,
        name=person.name,
        is_unknown=person.is_unknown,
        count=count,
        fav_count=fav_count,
        portrait_face_id=portrait_face.id if portrait_face is not None else None,
        group_name=person.group_name,
        created_at=person.created_at,
        linked_entity=EntityRefDto(id=linked_entity.id, title=linked_entity.title, type=linked_entity.type)
        if linked_entity is not None
        else None,
    )


def _person_instance_counts(session: Session) -> dict[int, tuple[int, int]]:
    """Grouped (count, fav_count) per person_id — one query instead of 2×N."""
    rows = session.execute(
        select(
            AssetInstance.person_id,
            func.count(AssetInstance.id),
            func.sum(case((AssetInstance.favourite.is_(True), 1), else_=0)),
        )
        .where(AssetInstance.deleted_at.is_(None))
        .group_by(AssetInstance.person_id)
    ).all()
    return {
        person_id: (count, int(fav_count or 0))
        for person_id, count, fav_count in rows
    }


def _person_portrait_face_ids(session: Session) -> dict[int, int]:
    """Best face (highest score, NULLs last) per person_id — one query instead of N."""
    ranked = (
        select(
            Face.person_id,
            Face.id,
            func.row_number()
            .over(partition_by=Face.person_id, order_by=Face.score.desc().nulls_last())
            .label("rank"),
        )
        .where(Face.person_id.is_not(None))
        .subquery()
    )
    rows = session.execute(
        select(ranked.c.person_id, ranked.c.id).where(ranked.c.rank == 1)
    ).all()
    return dict(rows)


@router.post("", response_model=PersonDto, status_code=201)
async def create_person(body: CreatePersonRequest, session: DbSession, vault: VaultDep) -> PersonDto:
    """Create a new named person and ensure their folder exists."""
    from photofant.config import get_data_root
    from photofant.media.person_folders import ensure_person_folder

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name must not be empty")

    new_person = Person(name=name, is_unknown=False, created_at=datetime.now(UTC).replace(tzinfo=None))
    session.add(new_person)
    session.flush()

    data_root = get_data_root()
    ensure_person_folder(data_root, new_person)

    session.commit()
    session.refresh(new_person)

    log.info("Created person %d with name %r", new_person.id, new_person.name)
    return _build_person_dto(session, new_person, vault)


@router.get("", response_model=list[PersonDto])
async def list_persons(session: DbSession, vault: VaultDep) -> list[PersonDto]:
    persons = (
        session.query(Person)
        .order_by(Person.is_unknown.asc(), Person.id.asc())
        .all()
    )
    counts = _person_instance_counts(session)
    portrait_face_ids = _person_portrait_face_ids(session)
    linked_entities = KnowledgeService(session, vault).linked_entity_refs(
        "person", [person.id for person in persons]
    )

    return [
        PersonDto(
            id=person.id,
            name=person.name,
            is_unknown=person.is_unknown,
            count=counts.get(person.id, (0, 0))[0],
            fav_count=counts.get(person.id, (0, 0))[1],
            portrait_face_id=portrait_face_ids.get(person.id),
            group_name=person.group_name,
            created_at=person.created_at,
            linked_entity=(
                EntityRefDto(id=ref.id, title=ref.title, type=ref.type)
                if (ref := linked_entities.get(person.id)) is not None
                else None
            ),
        )
        for person in persons
    ]


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
async def update_person(
    person_id: int, body: UpdatePersonRequest, session: DbSession, vault: VaultDep
) -> PersonDto:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    if body.name is None and body.group_name is None:
        raise HTTPException(status_code=422, detail="Nothing to update")

    if body.name is not None:
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
        log.info("Renamed person %d to %r", person_id, person.name)

    if body.group_name is not None:
        person.group_name = body.group_name.strip() or None

    session.commit()
    session.refresh(person)
    return _build_person_dto(session, person, vault)


@router.post("/{person_id}/link-entity", response_model=PersonDto)
async def link_person_entity(
    person_id: int, body: LinkEntityRequest, session: DbSession, vault: VaultDep
) -> PersonDto:
    """Verknüpft eine Person mit einer Wissens-Entity (P24). Überlebt Cache-Rebuild —
    die Verknüpfung lebt im Vault-Frontmatter (``media_links.persons``), der Cache ist
    nur die Projektion."""
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    service = KnowledgeService(session, vault)
    try:
        service.link_media(body.entity_id, "person", person_id, _parse_owner(body.owner))
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OwnershipConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    session.commit()

    log.info("Linked person %d → entity %r", person_id, body.entity_id)
    return _build_person_dto(session, person, vault)


@router.delete("/{person_id}/link-entity", response_model=PersonDto)
async def unlink_person_entity(
    person_id: int,
    entity_id: str,
    session: DbSession,
    vault: VaultDep,
    owner: str = Owner.USER.value,
) -> PersonDto:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    service = KnowledgeService(session, vault)
    try:
        service.unlink_media(entity_id, "person", person_id, _parse_owner(owner))
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OwnershipConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    session.commit()

    log.info("Unlinked person %d from entity %r", person_id, entity_id)
    return _build_person_dto(session, person, vault)


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
        from photofant.jobs.recommendation_job import invalidate_recommendations

        invalidate_recommendations(session, asset_ids)
        session.commit()

        from photofant.jobs.collections_job import enqueue_reevaluate_assets
        asyncio.ensure_future(enqueue_reevaluate_assets(asset_ids))

    return MergeResultDto(
        faces_moved=result["faces_moved"],
        instances_moved=result["instances_moved"],
    )


@router.delete("/{person_id}", response_model=MergeResultDto)
async def delete_person_endpoint(person_id: int, session: DbSession, vault: VaultDep) -> MergeResultDto:
    """Delete a person — faces and photos move to _unknown, folder + row are gone."""
    from photofant.config import get_data_root
    from photofant.media.person_folders import delete_person

    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    if person.is_unknown:
        raise HTTPException(status_code=400, detail="Cannot delete the unknown person")

    # Waisen-Schutz (P24): eine gelöschte Person darf keine Verknüpfung in einer
    # Entity zurücklassen — sonst zeigt media_links.persons auf eine tote ID.
    service = KnowledgeService(session, vault)
    linked = service.linked_entity_ref("person", person_id)
    if linked is not None:
        service.unlink_media(linked.id, "person", person_id, Owner.USER)
        session.commit()

    data_root = get_data_root()
    result = await asyncio.to_thread(delete_person, session, person_id, data_root)
    session.commit()
    log.info("Deleted person %d", person_id)

    asset_ids = result["asset_ids"]
    if asset_ids:
        from photofant.jobs.recommendation_job import invalidate_recommendations

        invalidate_recommendations(session, asset_ids)
        session.commit()

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


@router.post("/{person_id}/bulk-assign", response_model=PersonImportResponse)
async def bulk_assign_to_person(
    person_id: int,
    body: BulkAssignRequest,
    session: DbSession,
) -> PersonImportResponse:
    """Assign a selection of assets to an existing named person as a background job."""
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    if person.is_unknown:
        raise HTTPException(status_code=400, detail="Cannot assign to unknown person")
    if not body.asset_ids:
        raise HTTPException(status_code=422, detail="asset_ids must not be empty")

    from photofant.jobs.bulk_assign_person_job import enqueue_bulk_assign_person

    status = await enqueue_bulk_assign_person(body.asset_ids, person_id)
    return PersonImportResponse(job_id=status.id)


@router.post("/{person_id}/reveal", status_code=204)
async def reveal_person_folder(person_id: int, session: DbSession) -> None:
    """Open the person's folder in the system file browser (Windows Explorer)."""
    from photofant.config import get_data_root
    from photofant.media.person_folders import ensure_person_folder

    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    data_root = get_data_root()
    person_dir = ensure_person_folder(data_root, person)

    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(person_dir)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(person_dir)])
    else:
        subprocess.Popen(["xdg-open", str(person_dir)])


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

    asset_ids = result["asset_ids"]
    if asset_ids:
        from photofant.jobs.recommendation_job import invalidate_recommendations

        invalidate_recommendations(session, asset_ids)
        session.commit()

        from photofant.jobs.collections_job import enqueue_reevaluate_assets
        asyncio.ensure_future(enqueue_reevaluate_assets(asset_ids))

    return SplitResultDto(
        new_person_id=result["new_person_id"],
        faces_moved=result["faces_moved"],
        instances_created=result["instances_created"],
    )
