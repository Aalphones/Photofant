"""Classify API — trigger batch reprocessing of classification steps."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from photofant.jobs.queue import JobStatus

router = APIRouter(prefix="/classify")

ClassifyStep = Literal["tags", "caption", "embedding", "heuristics", "faces", "categories"]


class RerunRequest(BaseModel):
    asset_ids: list[int] | Literal["all"]
    steps: list[ClassifyStep]
    caption_preset_id: int | None = None

    @field_validator("steps")
    @classmethod
    def steps_not_empty(cls, steps: list[ClassifyStep]) -> list[ClassifyStep]:
        if not steps:
            raise ValueError("steps must contain at least one entry")
        return steps


class RerunResponse(BaseModel):
    job_id: str


@router.post("/rerun", response_model=RerunResponse)
async def trigger_rerun(body: RerunRequest) -> RerunResponse:
    from photofant.jobs.rerun_job import enqueue_rerun

    status: JobStatus = await enqueue_rerun(
        body.asset_ids, body.steps, body.caption_preset_id
    )
    return RerunResponse(job_id=status.id)
