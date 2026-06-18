from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import desc
from sqlalchemy.orm import Query as OrmQuery
from sqlalchemy.orm import Session

from photofant.api.assets import AssetDto, build_asset_dto
from photofant.config import get_data_root
from photofant.db.cache import get_cache_db_path
from photofant.db.models import Asset, AssetInstance
from photofant.db.session import get_session
from photofant.media import moves

router = APIRouter(prefix="/trash")

DbSession = Annotated[Session, Depends(get_session)]


def _trash_query(session: Session) -> OrmQuery[Any]:
    return (
        session.query(Asset, AssetInstance)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(AssetInstance.deleted_at.is_not(None))
    )


def _deleted_rows(session: Session) -> list[tuple[Asset, AssetInstance]]:
    return _trash_query(session).order_by(desc(AssetInstance.deleted_at)).all()


def _deleted_row(session: Session, asset_id: int) -> tuple[Asset, AssetInstance] | None:
    return _trash_query(session).filter(Asset.id == asset_id).first()


@router.get("", response_model=list[AssetDto])
async def list_trash(session: DbSession) -> list[AssetDto]:
    return [build_asset_dto(asset, instance) for asset, instance in _deleted_rows(session)]


@router.post("/{asset_id}/restore", response_model=AssetDto)
async def restore_asset(asset_id: int, session: DbSession) -> AssetDto:
    row = _deleted_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not in trash")

    asset, instance = row
    data_root = get_data_root()
    await moves.restore(session, instance, data_root)
    return build_asset_dto(asset, instance)


@router.delete("/{asset_id}", status_code=204)
async def purge_asset(asset_id: int, session: DbSession) -> Response:
    row = _deleted_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not in trash")

    _, instance = row
    await moves.purge(session, instance, get_cache_db_path())
    return Response(status_code=204)


@router.delete("", status_code=204)
async def empty_trash(session: DbSession) -> Response:
    cache_db_path = get_cache_db_path()
    for _, instance in _deleted_rows(session):
        await moves.purge(session, instance, cache_db_path)
    return Response(status_code=204)
