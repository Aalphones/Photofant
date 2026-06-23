"""CRUD API for Flux2-Edit prompt templates (P9 Phase 4, Konzept §8.4)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.db.models import PromptTemplate
from photofant.db.session import get_session

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])

DbSession = Annotated[Session, Depends(get_session)]


class PromptTemplateDto(BaseModel):
    id: int
    name: str
    prompt: str
    params: dict[str, Any] | None
    created_at: datetime | None


class CreatePromptTemplateRequest(BaseModel):
    name: str
    prompt: str
    params: dict[str, Any] | None = None


class UpdatePromptTemplateRequest(BaseModel):
    name: str | None = None
    prompt: str | None = None
    params: dict[str, Any] | None = None


def _to_dto(row: PromptTemplate) -> PromptTemplateDto:
    return PromptTemplateDto(
        id=row.id,
        name=row.name,
        prompt=row.prompt,
        params=row.params,
        created_at=row.created_at,
    )


@router.get("", response_model=list[PromptTemplateDto])
async def list_prompt_templates(session: DbSession) -> list[PromptTemplateDto]:
    rows = session.query(PromptTemplate).order_by(PromptTemplate.id).all()
    return [_to_dto(row) for row in rows]


@router.post("", response_model=PromptTemplateDto, status_code=201)
async def create_prompt_template(
    body: CreatePromptTemplateRequest, session: DbSession
) -> PromptTemplateDto:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="name must not be empty")
    if not body.prompt.strip():
        raise HTTPException(status_code=422, detail="prompt must not be empty")

    row = PromptTemplate(
        name=body.name.strip(),
        prompt=body.prompt.strip(),
        params=body.params,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_dto(row)


@router.patch("/{template_id}", response_model=PromptTemplateDto)
async def update_prompt_template(
    template_id: int, body: UpdatePromptTemplateRequest, session: DbSession
) -> PromptTemplateDto:
    row = session.get(PromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")

    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(status_code=422, detail="name must not be empty")
        row.name = body.name.strip()
    if body.prompt is not None:
        if not body.prompt.strip():
            raise HTTPException(status_code=422, detail="prompt must not be empty")
        row.prompt = body.prompt.strip()
    if body.params is not None:
        row.params = body.params

    session.commit()
    session.refresh(row)
    return _to_dto(row)


@router.delete("/{template_id}", status_code=204)
async def delete_prompt_template(template_id: int, session: DbSession) -> None:
    row = session.get(PromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    session.delete(row)
    session.commit()
