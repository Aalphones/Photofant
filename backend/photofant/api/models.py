"""GET /api/models, POST /api/models/{id}/download, POST /api/models/scan."""
from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.config import get_models_dir
from photofant.db.models import ModelRegistry
from photofant.db.session import get_session
from photofant.jobs.download_job import ScanResult, enqueue_download, scan_models_dir
from photofant.models.loader import ManifestEntry, get_manifest_entry, load_manifest

log = logging.getLogger(__name__)

router = APIRouter(prefix="/models")

DbSession = Annotated[Session, Depends(get_session)]


class ModelStatus(StrEnum):
    MISSING = "missing"
    AVAILABLE = "available"
    ACTIVE = "active"
    INPLACE = "inplace"


class ModelDto(BaseModel):
    id: str
    role: str
    name: str
    variant: str | None
    format: str
    path: str | None
    sha256: str | None
    managed: bool
    enabled: bool
    is_default: bool
    status: str
    size_bytes: int | None
    license_note: str | None


class CapabilitiesDto(BaseModel):
    faces: bool
    tagging: bool
    captioning: bool
    semantic_search: bool
    rembg: bool


def _derive_status(entry: ManifestEntry, row: ModelRegistry | None) -> ModelStatus:
    """Compute display status from manifest entry + optional registry row."""
    if row is None:
        return ModelStatus.MISSING

    if not row.managed:
        return ModelStatus.INPLACE

    path_str = row.path
    file_present = path_str is not None and Path(path_str).exists()

    if row.enabled and file_present:
        return ModelStatus.ACTIVE

    if not file_present:
        return ModelStatus.MISSING

    return ModelStatus.AVAILABLE


@router.get("", response_model=list[ModelDto])
def list_models(session: DbSession) -> list[ModelDto]:
    """Return all manifest models joined with their registry state."""
    manifest_entries = load_manifest()
    registry_rows: dict[str, ModelRegistry] = {
        row.manifest_id: row
        for row in session.query(ModelRegistry).all()
    }

    result: list[ModelDto] = []
    for entry in manifest_entries:
        row = registry_rows.get(entry.id)
        status = _derive_status(entry, row)

        result.append(ModelDto(
            id=entry.id,
            role=entry.role,
            name=entry.name,
            variant=entry.variant,
            format=entry.format,
            path=row.path if row else None,
            sha256=row.sha256 if row else None,
            managed=row.managed if row else True,
            enabled=row.enabled if row else False,
            is_default=row.is_default if row else False,
            status=status,
            size_bytes=entry.size_bytes,
            license_note=entry.license_note,
        ))

    return result


class DownloadRequest(BaseModel):
    license_ack: bool = False


class DownloadResponse(BaseModel):
    job_id: str


class ScanResponse(BaseModel):
    registered: list[ScanResult]


@router.post("/{manifest_id}/download", response_model=DownloadResponse)
async def download_model(
    manifest_id: str,
    body: DownloadRequest,
    session: DbSession,
) -> DownloadResponse:
    """Enqueue a managed download for a manifest model.

    Returns 409 with code LICENSE_ACK_REQUIRED if the model requires explicit
    license acknowledgement and body.license_ack is False (Phase 4 handles dialog).
    """
    entry = get_manifest_entry(manifest_id)
    if entry is None:
        raise HTTPException(status_code=404, detail={"code": "MODEL_NOT_FOUND"})

    if entry.requires_license_ack and not body.license_ack:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "LICENSE_ACK_REQUIRED",
                "license_note": entry.license_note,
            },
        )

    models_dir = get_models_dir(session)
    job_status = await enqueue_download(manifest_id, models_dir)
    return DownloadResponse(job_id=job_status.id)


@router.post("/scan", response_model=ScanResponse)
async def scan_models(session: DbSession) -> ScanResponse:
    """Scan models_dir for manually placed files and register matched entries."""
    models_dir = get_models_dir(session)
    found = await asyncio.to_thread(scan_models_dir, models_dir)
    return ScanResponse(registered=found)


@router.get("/capabilities", response_model=CapabilitiesDto)
def get_capabilities(session: DbSession) -> CapabilitiesDto:
    """Derive feature flags from enabled + reachable registry rows."""
    enabled_roles: set[str] = set()

    for row in session.query(ModelRegistry).filter(ModelRegistry.enabled == True).all():  # noqa: E712
        path_ok = (
            row.path is not None and Path(row.path).exists()
        ) or (
            not row.managed  # in-place: trust that path was validated at bind time
        )
        if path_ok:
            enabled_roles.add(row.role)

    return CapabilitiesDto(
        faces="face" in enabled_roles,
        tagging="tagger" in enabled_roles,
        captioning="captioner" in enabled_roles,
        semantic_search="semantic_search" in enabled_roles,
        rembg="rembg" in enabled_roles,
    )
