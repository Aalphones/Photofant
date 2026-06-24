"""Export endpoints — favourites and general reveal.

All write operations run as background jobs so the UI never blocks.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from photofant.jobs.export_job import (
    enqueue_export_by_person,
    enqueue_export_filter,
    enqueue_export_random,
    reveal_export_folder,
)

router = APIRouter(prefix="/export")


class JobStarted(BaseModel):
    job_id: str


class ExportFilterRequest(BaseModel):
    sources: list[str] | None = None
    quality_min: float | None = Field(None, ge=0.0, le=1.0)
    tag_ids: list[int] | None = None
    person_id: int | None = None
    include_versions: bool = False


class ExportRandomRequest(BaseModel):
    count: int = Field(5, ge=1, le=100)
    images_per_set: int = Field(100, ge=1, le=10_000)


@router.get("/reveal", status_code=204)
async def reveal() -> None:
    """Open the _export folder in the system file browser."""
    reveal_export_folder()


@router.post("/favourites/filter", response_model=JobStarted, status_code=202)
async def export_favourites_filter(body: ExportFilterRequest) -> JobStarted:
    """Export all favourites matching the given filter to a dated export folder."""
    status = await enqueue_export_filter(
        source_filter=body.sources or None,
        quality_min=body.quality_min,
        tag_ids=body.tag_ids or None,
        person_id=body.person_id,
        include_versions=body.include_versions,
    )
    return JobStarted(job_id=status.id)


@router.post("/favourites/by-person", response_model=JobStarted, status_code=202)
async def export_favourites_by_person() -> JobStarted:
    """Export all favourites into per-person sub-folders."""
    status = await enqueue_export_by_person()
    return JobStarted(job_id=status.id)


@router.post("/favourites/random", response_model=JobStarted, status_code=202)
async def export_favourites_random(body: ExportRandomRequest) -> JobStarted:
    """Export random distinct favourites — count sets × images each, no duplicates within a set."""
    status = await enqueue_export_random(
        count=body.count,
        images_per_set=body.images_per_set,
    )
    return JobStarted(job_id=status.id)
