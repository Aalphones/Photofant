"""Tags endpoint — list, rename, merge and bulk-tag operations."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetTag, Tag
from photofant.db.session import get_session

router = APIRouter(prefix="/tags")

DbSession = Annotated[Session, Depends(get_session)]

log = logging.getLogger(__name__)


class TagListItem(BaseModel):
    id: int
    name: str
    count: int
    alias_of: int | None = None


class RenameTagRequest(BaseModel):
    name: str


class MergeTagsRequest(BaseModel):
    from_ids: list[int]
    into_id: int


class BulkTagRequest(BaseModel):
    asset_ids: list[int]
    add: list[str]   # tag names → upsert as kind=manual
    remove: list[int]  # tag ids to remove from all given assets


def _upsert_tag(session: Session, name: str) -> Tag:
    """Upsert a tag by canonical name; resolves aliases to the canonical tag."""
    normalized = name.strip().lower().replace(" ", "_")
    tag = session.query(Tag).filter_by(name=normalized).first()
    if tag is None:
        tag = Tag(name=normalized)
        session.add(tag)
        session.flush()
    # If this tag is itself an alias, return the canonical
    if tag.alias_of is not None:
        canonical = session.get(Tag, tag.alias_of)
        if canonical is not None:
            return canonical
    return tag


@router.get("", response_model=list[TagListItem])
async def list_tags(
    session: DbSession,
    query: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
) -> list[TagListItem]:
    q = (
        session.query(Tag.id, Tag.name, Tag.alias_of, func.count(AssetTag.id).label("cnt"))
        .outerjoin(AssetTag, (AssetTag.tag_id == Tag.id) & (AssetTag.manually_removed.is_(False)))
        .group_by(Tag.id, Tag.name, Tag.alias_of)
    )
    if query:
        q = q.filter(Tag.name.ilike(f"%{query}%"))
    rows = (
        q.order_by(func.count(AssetTag.id).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [TagListItem(id=row.id, name=row.name, count=row.cnt, alias_of=row.alias_of) for row in rows]


@router.post("/merge", status_code=204)
async def merge_tags(body: MergeTagsRequest, session: DbSession) -> Response:
    """Merge multiple tags into one canonical tag; merged tags become aliases."""
    canonical = session.get(Tag, body.into_id)
    if canonical is None:
        raise HTTPException(status_code=404, detail="Target tag not found")

    for from_id in body.from_ids:
        if from_id == body.into_id:
            continue
        source = session.get(Tag, from_id)
        if source is None:
            continue

        # Re-point all asset_tags from the source tag to the canonical
        existing_rows = session.query(AssetTag).filter_by(tag_id=from_id).all()
        for row in existing_rows:
            existing_in_canonical = (
                session.query(AssetTag)
                .filter_by(asset_id=row.asset_id, tag_id=body.into_id)
                .first()
            )
            if existing_in_canonical is None:
                row.tag_id = body.into_id
            else:
                # Prefer higher score; preserve manual kind
                if row.kind == "manual":
                    existing_in_canonical.kind = "manual"
                if row.score is not None and (
                    existing_in_canonical.score is None or row.score > existing_in_canonical.score
                ):
                    existing_in_canonical.score = row.score
                session.delete(row)

        source.alias_of = body.into_id
        log.info("Merged tag %d (%s) → %d (%s)", from_id, source.name, body.into_id, canonical.name)

    session.commit()
    return Response(status_code=204)


@router.post("/bulk", status_code=204)
async def bulk_tag(body: BulkTagRequest, session: DbSession) -> Response:
    """Add/remove tags on a list of assets at once."""
    if not body.asset_ids:
        raise HTTPException(status_code=422, detail="asset_ids must not be empty")

    # Resolve add-names to tag objects (upsert)
    add_tags: list[Tag] = [_upsert_tag(session, name) for name in body.add]

    for asset_id in body.asset_ids:
        asset = session.get(Asset, asset_id)
        if asset is None:
            continue

        for tag in add_tags:
            existing = session.query(AssetTag).filter_by(asset_id=asset_id, tag_id=tag.id).first()
            if existing is None:
                session.add(AssetTag(asset_id=asset_id, tag_id=tag.id, kind="manual"))
            else:
                existing.kind = "manual"
                existing.manually_removed = False

        for tag_id in body.remove:
            existing = session.query(AssetTag).filter_by(asset_id=asset_id, tag_id=tag_id).first()
            if existing is None:
                continue
            if existing.kind == "manual":
                session.delete(existing)
            else:
                existing.manually_removed = True

    session.commit()
    log.info(
        "Bulk-tag: %d asset(s), +%d tags, -%d tags",
        len(body.asset_ids), len(add_tags), len(body.remove),
    )
    return Response(status_code=204)


@router.patch("/{tag_id}", response_model=TagListItem)
async def rename_tag(tag_id: int, body: RenameTagRequest, session: DbSession) -> TagListItem:
    """Rename a tag (canonical name; must be unique)."""
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")

    normalized = body.name.strip().lower().replace(" ", "_")
    if not normalized:
        raise HTTPException(status_code=422, detail="name must not be empty")

    conflict = session.query(Tag).filter(Tag.name == normalized, Tag.id != tag_id).first()
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Tag name already exists")

    tag.name = normalized
    session.commit()
    session.refresh(tag)

    count = (
        session.query(func.count(AssetTag.id))
        .filter(AssetTag.tag_id == tag_id, AssetTag.manually_removed.is_(False))
        .scalar()
        or 0
    )
    return TagListItem(id=tag.id, name=tag.name, count=count, alias_of=tag.alias_of)
