"""Persons API — list and rename Person records.

GET   /api/persons       → PersonDto[] (sorted by count desc, unknown last)
PATCH /api/persons/{id}  → rename → PersonDto
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
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


class RenameRequest(BaseModel):
    name: str


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


@router.get("", response_model=list[PersonDto])
async def list_persons(session: DbSession) -> list[PersonDto]:
    persons = (
        session.query(Person)
        .order_by(Person.is_unknown.asc(), Person.id.asc())
        .all()
    )
    return [_build_person_dto(session, person) for person in persons]


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
    person.name = new_name
    session.commit()
    session.refresh(person)
    log.info("Renamed person %d to %r", person_id, person.name)
    return _build_person_dto(session, person)
