from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Query as OrmQuery, Session

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance
from photofant.db.session import get_session
from photofant.jobs.import_job import enqueue_import, enqueue_scan

router = APIRouter(prefix="/assets")

DbSession = Annotated[Session, Depends(get_session)]


class SortField(StrEnum):
    DATE = "date"
    SIZE = "size"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class AssetDto(BaseModel):
    id: int
    content_hash: str
    width: int | None
    height: int | None
    file_size: int | None
    format: str | None
    source: str | None
    created_at: datetime | None
    imported_at: datetime | None
    favourite: bool
    version_count: int
    generation_meta: dict | None  # type: ignore[type-arg]


class AssetDetailDto(AssetDto):
    path: str | None


class AssetsPage(BaseModel):
    items: list[AssetDto]
    total: int
    page: int
    page_size: int


class ImportRequest(BaseModel):
    paths: list[str]


class JobStarted(BaseModel):
    job_id: str


def _to_dto(asset: Asset, instance: AssetInstance) -> AssetDto:
    return AssetDto(
        id=asset.id,
        content_hash=asset.content_hash,
        width=asset.width,
        height=asset.height,
        file_size=asset.file_size,
        format=asset.format,
        source=asset.source,
        created_at=asset.created_at,
        imported_at=asset.imported_at,
        favourite=instance.favourite,
        version_count=0,  # version table added in P8
        generation_meta=asset.generation_meta,
    )


def _base_query(session: Session) -> OrmQuery[Any]:
    return (
        session.query(Asset, AssetInstance)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(AssetInstance.deleted_at.is_(None))
    )


@router.get("", response_model=AssetsPage)
async def list_assets(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    sort: SortField = SortField.DATE,
    order: SortOrder = SortOrder.DESC,
    favourite: bool | None = None,
) -> AssetsPage:
    query = _base_query(session)

    if favourite is not None:
        query = query.filter(AssetInstance.favourite.is_(favourite))

    sort_col: Any
    if sort == SortField.DATE:
        sort_col = func.coalesce(Asset.created_at, Asset.imported_at)
    else:
        sort_col = Asset.file_size

    order_fn = asc if order == SortOrder.ASC else desc
    query = query.order_by(order_fn(sort_col))

    total: int = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [_to_dto(asset, instance) for asset, instance in rows]
    return AssetsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{asset_id}", response_model=AssetDetailDto)
async def get_asset(asset_id: int, session: DbSession) -> AssetDetailDto:
    row = (
        session.query(Asset, AssetInstance)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(Asset.id == asset_id, AssetInstance.deleted_at.is_(None))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    base = _to_dto(asset, instance)
    return AssetDetailDto(**base.model_dump(), path=instance.path)


@router.post("/import", response_model=JobStarted)
async def import_assets(body: ImportRequest, session: DbSession) -> JobStarted:
    if not body.paths:
        raise HTTPException(status_code=422, detail="paths must not be empty")
    status = await enqueue_import(body.paths)
    return JobStarted(job_id=status.id)


@router.post("/scan", response_model=JobStarted)
async def scan_assets(session: DbSession) -> JobStarted:
    data_root = get_data_root(session)
    status = await enqueue_scan(Path(data_root))
    return JobStarted(job_id=status.id)
