"""Tags endpoint — list tags with usage counts (autocomplete + management)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from photofant.db.models import AssetTag, Tag
from photofant.db.session import get_session

router = APIRouter(prefix="/tags")

DbSession = Annotated[Session, Depends(get_session)]


class TagListItem(BaseModel):
    id: int
    name: str
    count: int


@router.get("", response_model=list[TagListItem])
async def list_tags(
    session: DbSession,
    query: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TagListItem]:
    q = (
        session.query(Tag.id, Tag.name, func.count(AssetTag.id).label("cnt"))
        .outerjoin(AssetTag, AssetTag.tag_id == Tag.id)
        .group_by(Tag.id, Tag.name)
    )
    if query:
        q = q.filter(Tag.name.ilike(f"%{query}%"))
    rows = (
        q.order_by(func.count(AssetTag.id).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [TagListItem(id=row.id, name=row.name, count=row.cnt) for row in rows]
