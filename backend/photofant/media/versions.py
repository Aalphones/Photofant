"""Shared Version-row helpers — genutzt vom Crop-Editor-Speicherpfad (edit_sessions.py) UND vom
ComfyUI-Face-Upscale-Auto-Import (comfyui_run_job.py), damit beide Pfade exakt dasselbe
Version-Anlage-Muster teilen statt still auseinanderzudriften."""
from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.orm import Session

from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
from photofant.db.models import Version
from photofant.media.thumbnails import generate_thumbnail


def unset_current_versions(db: Session, instance_id: int | None, face_id: int | None) -> None:
    query = db.query(Version).filter(Version.is_current.is_(True))
    if instance_id is not None:
        query = query.filter(Version.instance_id == instance_id)
    else:
        query = query.filter(Version.face_id == face_id)
    for version in query.all():
        version.is_current = False


async def generate_version_thumbnail(version_id: int, file_path: Path) -> None:
    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for size in (256, 512):
        thumb = await asyncio.to_thread(generate_thumbnail, file_path, size)
        await asyncio.to_thread(store_thumbnail, cache_path, version_id, size, thumb, "edit")
