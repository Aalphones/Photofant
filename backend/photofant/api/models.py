"""GET /api/models, POST /api/models/{id}/download, POST /api/models/scan."""
from __future__ import annotations

import asyncio
import logging
import shutil
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.config import get_models_dir
from photofant.db.models import ModelRegistry
from photofant.db.session import get_session
from photofant.jobs.download_job import ScanResult, enqueue_download, scan_models_dir
from photofant.models.loader import ManifestEntry, get_manifest_entry, load_manifest
from photofant.models.validation import (
    ModelErrorCode,
    ModelValidationError,
    validate_component_model,
    validate_in_place,
)
from photofant.models.vram import detect_gpu, recommend_variant

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
    components: dict[str, Any] | None = None
    sha256: str | None
    managed: bool
    enabled: bool
    is_default: bool
    status: str
    size_bytes: int | None
    license_note: str | None
    caption_mode: str | None
    capabilities: dict[str, Any] | None


class CapabilitiesDto(BaseModel):
    faces: bool
    tagging: bool
    captioning: bool
    semantic_search: bool
    rembg: bool
    heavy_caption: bool


def _derive_status(entry: ManifestEntry, row: ModelRegistry | None) -> ModelStatus:
    """Compute display status from manifest entry + optional registry row."""
    if row is None:
        return ModelStatus.MISSING

    if not row.managed:
        if entry.is_component_model:
            components = row.components or {}
            required = [
                key for key, spec in entry.components_spec.items()
                if spec.get("required", False)
            ]
            if not all(components.get(key) for key in required):
                return ModelStatus.MISSING
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
            components=row.components if row else None,
            sha256=row.sha256 if row else None,
            managed=row.managed if row else True,
            enabled=row.enabled if row else False,
            is_default=row.is_default if row else False,
            status=status,
            size_bytes=entry.size_bytes,
            license_note=entry.license_note,
            caption_mode=entry.caption_mode,
            capabilities=entry.capabilities,
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

    models_dir = get_models_dir()
    job_status = await enqueue_download(manifest_id, models_dir)
    return DownloadResponse(job_id=job_status.id)


@router.post("/scan", response_model=ScanResponse)
async def scan_models(session: DbSession) -> ScanResponse:
    """Scan models_dir for manually placed files and register matched entries."""
    models_dir = get_models_dir()
    found = await asyncio.to_thread(scan_models_dir, models_dir)
    return ScanResponse(registered=found)


class RegisterLocalRequest(BaseModel):
    manifest_id: str
    path: str | None = None
    components: dict[str, str] | None = None


class ComponentWarningResponse(BaseModel):
    model: ModelDto
    warnings: list[str]


@router.post("/register-local", response_model=ComponentWarningResponse)
async def register_local(body: RegisterLocalRequest, session: DbSession) -> ComponentWarningResponse:
    """Bind an already-present file/folder to a manifest slot without copying it.

    Runs the §12.2a validation pipeline first; only on success is a `managed = 0`
    registry row written. A failed validation returns a structured 422 and leaves
    both the DB and the filesystem untouched.

    For component models (e.g. Flux), `components` is a map of component paths.
    For single-file/folder models, `path` is the file/folder path.
    """
    entry = get_manifest_entry(body.manifest_id)
    if entry is None:
        raise HTTPException(status_code=404, detail={"code": ModelErrorCode.NOT_FOUND})

    warnings: list[str] = []

    if entry.is_component_model:
        if not body.components:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": ModelErrorCode.INCOMPLETE,
                    "expected": "Komponenten-Map mit Pfaden",
                    "found": "keine Komponenten angegeben",
                    "next_step": "Pfade für alle Komponenten (Transformer, Text-Encoder, VAE) angeben.",
                },
            )
        try:
            comp_result = await asyncio.to_thread(
                validate_component_model, entry, body.components,
            )
        except ModelValidationError as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": error.code,
                    "expected": error.expected,
                    "found": error.found,
                    "next_step": error.next_step,
                },
            ) from error

        warnings = comp_result.warnings
        sha256 = next(iter(comp_result.component_hashes.values()), None)

        row = session.query(ModelRegistry).filter(ModelRegistry.manifest_id == entry.id).first()
        if row is None:
            row = ModelRegistry(manifest_id=entry.id)
            session.add(row)

        row.role = entry.role
        row.name = entry.name
        row.variant = entry.variant
        row.format = entry.format
        row.path = None
        row.components = body.components
        row.sha256 = sha256
        row.managed = False
        row.enabled = True
        row.caption_mode = entry.caption_mode
        row.capabilities = entry.capabilities
        session.commit()
        session.refresh(row)

        log.info("Registered component model %s with %d components", entry.id, len(body.components))
    else:
        if not body.path:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": ModelErrorCode.NOT_FOUND,
                    "expected": "Pfad zur Datei oder zum Ordner",
                    "found": "kein Pfad angegeben",
                    "next_step": "Einen Pfad angeben.",
                },
            )
        try:
            validation = await asyncio.to_thread(validate_in_place, entry, body.path)
        except ModelValidationError as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": error.code,
                    "expected": error.expected,
                    "found": error.found,
                    "next_step": error.next_step,
                },
            ) from error

        row = session.query(ModelRegistry).filter(ModelRegistry.manifest_id == entry.id).first()
        if row is None:
            row = ModelRegistry(manifest_id=entry.id)
            session.add(row)

        row.role = entry.role
        row.name = entry.name
        row.variant = entry.variant
        row.format = entry.format
        row.path = body.path
        row.sha256 = validation.sha256
        row.managed = False
        row.enabled = True
        row.caption_mode = entry.caption_mode
        row.capabilities = entry.capabilities
        session.commit()
        session.refresh(row)

        log.info("Registered in-place model %s at %s", entry.id, body.path)

    dto = ModelDto(
        id=entry.id,
        role=entry.role,
        name=entry.name,
        variant=entry.variant,
        format=entry.format,
        path=row.path,
        components=row.components,
        sha256=row.sha256,
        managed=row.managed,
        enabled=row.enabled,
        is_default=row.is_default,
        status=_derive_status(entry, row),
        size_bytes=entry.size_bytes,
        license_note=entry.license_note,
        caption_mode=entry.caption_mode,
        capabilities=entry.capabilities,
    )
    return ComponentWarningResponse(model=dto, warnings=warnings)


class DeleteResponse(BaseModel):
    deleted: bool
    file_removed: bool


@router.delete("/{manifest_id}", response_model=DeleteResponse)
def delete_model(manifest_id: str, session: DbSession) -> DeleteResponse:
    """Remove a model from the registry.

    Managed models: delete the downloaded file/folder *and* the row. In-place
    models (`managed = 0`): delete only the row — the user's original file is
    referenced, not owned, and stays exactly where it is.
    """
    row = session.query(ModelRegistry).filter(ModelRegistry.manifest_id == manifest_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": ModelErrorCode.NOT_FOUND})

    was_managed = row.managed
    file_removed = False
    if was_managed and row.path:
        target = Path(row.path)
        try:
            if target.is_dir():
                shutil.rmtree(target)
                file_removed = True
            elif target.is_file():
                target.unlink()
                file_removed = True
        except OSError as error:
            log.warning("Could not remove managed model files at %s: %s", target, error)

    session.delete(row)
    session.commit()
    log.info("Removed model %s (managed=%s, file_removed=%s)", manifest_id, was_managed, file_removed)
    return DeleteResponse(deleted=True, file_removed=file_removed)


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
        heavy_caption="heavy_captioner" in enabled_roles,
    )


class GpuInfoDto(BaseModel):
    name: str | None
    vram_gb: float | None
    vram_bytes: int | None


class VramRecommendation(BaseModel):
    model_id: str
    recommended_variant: str | None


class VramResponse(BaseModel):
    gpu: GpuInfoDto
    recommendations: list[VramRecommendation]


@router.get("/vram", response_model=VramResponse)
async def get_vram() -> VramResponse:
    """Detect GPU VRAM and recommend variants for all generative models."""
    gpu_info = await asyncio.to_thread(detect_gpu)

    gpu_dto = GpuInfoDto(
        name=gpu_info.name if gpu_info else None,
        vram_gb=gpu_info.vram_gb if gpu_info else None,
        vram_bytes=gpu_info.vram_bytes if gpu_info else None,
    )

    recommendations: list[VramRecommendation] = []
    manifest_entries = load_manifest()
    for entry in manifest_entries:
        if entry.tier != "generativ" or not entry.variants:
            continue
        variant = recommend_variant(gpu_dto.vram_gb, entry.variants)
        recommendations.append(VramRecommendation(
            model_id=entry.id,
            recommended_variant=variant,
        ))

    return VramResponse(gpu=gpu_dto, recommendations=recommendations)
