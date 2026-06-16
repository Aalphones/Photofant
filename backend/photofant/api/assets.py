from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Query as OrmQuery
from sqlalchemy.orm import Session

from photofant.config import get_data_root
from photofant.db.cache import get_cache_db_path, get_thumbnail, init_cache_db, store_thumbnail
from photofant.db.models import Asset, AssetInstance
from photofant.db.session import get_session
from photofant.jobs.import_job import enqueue_import, enqueue_scan
from photofant.media import moves
from photofant.media.thumbnails import generate_thumbnail

router = APIRouter(prefix="/assets")

DbSession = Annotated[Session, Depends(get_session)]

_VALID_THUMB_SIZES = frozenset({256, 512})


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


class FavouriteRequest(BaseModel):
    value: bool


def build_asset_dto(asset: Asset, instance: AssetInstance) -> AssetDto:
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


def _active_row(session: Session, asset_id: int) -> tuple[Asset, AssetInstance] | None:
    return _base_query(session).filter(Asset.id == asset_id).first()


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

    items = [build_asset_dto(asset, instance) for asset, instance in rows]
    return AssetsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{asset_id}/thumbnail")
async def get_asset_thumbnail(
    asset_id: int,
    session: DbSession,
    size: Annotated[int, Query()] = 256,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
) -> Response:
    if size not in _VALID_THUMB_SIZES:
        raise HTTPException(status_code=422, detail="size must be 256 or 512")

    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    etag = f'"{asset.content_hash}-{size}"'

    if if_none_match == etag:
        return Response(status_code=304)

    db_path = get_cache_db_path()
    init_cache_db(db_path)
    data = await asyncio.to_thread(get_thumbnail, db_path, asset.id, size)

    if data is None:
        source_path = Path(instance.path)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Source file not found on disk")
        data = await asyncio.to_thread(generate_thumbnail, source_path, size)
        await asyncio.to_thread(store_thumbnail, db_path, asset.id, size, data)

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "ETag": etag,
            "Cache-Control": "max-age=31536000, immutable",
        },
    )


@router.get("/{asset_id}", response_model=AssetDetailDto)
async def get_asset(asset_id: int, session: DbSession) -> AssetDetailDto:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    base = build_asset_dto(asset, instance)
    return AssetDetailDto(**base.model_dump(), path=instance.path)


@router.post("/upload", response_model=JobStarted)
async def upload_assets(files: list[UploadFile] = File(...)) -> JobStarted:
    """Accept multipart uploads from the browser, save to a temp dir, enqueue import."""
    if not files:
        raise HTTPException(status_code=422, detail="No files provided")

    tmp_dir = Path(tempfile.mkdtemp(prefix="pf_upload_"))
    saved: list[str] = []
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
        dest = tmp_dir / (upload.filename or f"upload{suffix}")
        content = await upload.read()
        dest.write_bytes(content)
        saved.append(str(dest))

    status = await enqueue_import(saved)
    return JobStarted(job_id=status.id)


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


@router.patch("/{asset_id}/favourite", response_model=AssetDto)
async def set_asset_favourite(asset_id: int, body: FavouriteRequest, session: DbSession) -> AssetDto:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    await moves.set_favourite(session, instance, body.value)
    return build_asset_dto(asset, instance)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: int, session: DbSession) -> Response:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    _, instance = row
    data_root = get_data_root(session)
    await moves.soft_delete(session, instance, data_root)
    return Response(status_code=204)
