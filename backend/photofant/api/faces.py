"""Face API — thumbnail serving für erkannte Gesichter.

GET /faces/{face_id}/thumbnail  → JPEG-Thumbnail (256 px) aus Cache-DB;
                                   bei Cache-Miss aus crop_path generiert.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from photofant.db.cache import get_cache_db_path, get_thumbnail, init_cache_db, store_thumbnail
from photofant.db.models import Face
from photofant.db.session import get_session
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)

router = APIRouter(prefix="/faces")

DbSession = Annotated[Session, Depends(get_session)]


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
