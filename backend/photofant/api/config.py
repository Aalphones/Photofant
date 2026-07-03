"""GET /api/config, PATCH /api/config — app-wide configuration via settings.json."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from photofant.jobs.queue import job_queue
from photofant.settings import load_settings, patch_settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/config")


class ConfigResponse(BaseModel):
    data: dict[str, Any]
    reboot_required: bool | None = None


class ConfigPatchRequest(BaseModel):
    data: dict[str, Any]


@router.get("", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """Return all settings with defaults filled in. Password is never exposed."""
    data = dict(load_settings())
    data.pop("password", None)
    return ConfigResponse(data=data)


@router.patch("", response_model=ConfigResponse)
async def patch_config(body: ConfigPatchRequest) -> ConfigResponse:
    """Update one or more settings keys. Writes atomically to settings.json."""
    try:
        updated = patch_settings(body.data)
    except TypeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if "models_dir" in body.data:
        models_dir_raw = body.data["models_dir"]
        if models_dir_raw:
            Path(models_dir_raw).mkdir(parents=True, exist_ok=True)
            log.info("models_dir set to %s — directory ensured", models_dir_raw)

    # Live-resize the tagging/captioning worker pools — no backend restart needed.
    if "tagging_workers" in body.data:
        job_queue.resize_tagging_workers(updated["tagging_workers"])
        log.info("tagging worker pool resized to %d", updated["tagging_workers"])
    if "captioning_workers" in body.data:
        job_queue.resize_captioning_workers(updated["captioning_workers"])
        log.info("captioning worker pool resized to %d", updated["captioning_workers"])

    reboot_required = "data_root" in body.data or None
    log.info("config patched: %s", list(body.data.keys()))
    return ConfigResponse(data=dict(updated), reboot_required=reboot_required)
