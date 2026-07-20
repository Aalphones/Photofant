from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

router = APIRouter(prefix="/jobs")


class JobDto(BaseModel):
    id: str
    kind: str
    label: str
    progress: float
    state: str
    error: str | None
    result: dict[str, Any] | None = None


def _to_dto(status: JobStatus) -> JobDto:
    return JobDto(
        id=status.id,
        kind=status.kind,
        label=status.label,
        progress=status.progress,
        state=status.state,
        error=status.error,
        result=status.result,
    )


async def _event_generator() -> AsyncGenerator[dict[str, str], None]:
    subscriber = job_queue.subscribe()
    try:
        for status in job_queue.snapshot():
            yield {"event": "job", "data": json.dumps(_to_dto(status).model_dump())}
        while True:
            try:
                status = await asyncio.wait_for(subscriber.get(), timeout=15.0)
                yield {"event": "job", "data": json.dumps(_to_dto(status).model_dump())}
            except TimeoutError:
                yield {"event": "ping", "data": ""}
    finally:
        job_queue.unsubscribe(subscriber)


@router.get("/stream")
async def jobs_stream() -> EventSourceResponse:
    return EventSourceResponse(_event_generator())


async def _demo_coro(status: JobStatus) -> None:
    steps = 5
    for step in range(1, steps + 1):
        await asyncio.sleep(1.0)
        job_queue.update(status, progress=step / steps, state=JobState.RUNNING)


class RunDemoResponse(BaseModel):
    job_id: str


@router.post("/demo", response_model=RunDemoResponse)
async def run_demo_job() -> RunDemoResponse:
    status = await job_queue.enqueue(
        kind=JobKind.DEMO,
        label="Demo-Job",
        coro_factory=_demo_coro,
    )
    return RunDemoResponse(job_id=status.id)


DupeScanScope = Literal["all", "selection"]


class DupeScanRequest(BaseModel):
    scope: DupeScanScope
    asset_ids: list[int] | None = None


@router.post("/dupe-scan", response_model=RunDemoResponse)
async def start_dupe_scan(body: DupeScanRequest) -> RunDemoResponse:
    from photofant.jobs.dupe_scan_job import enqueue_dupe_scan

    if body.scope == "selection" and not body.asset_ids:
        raise HTTPException(status_code=422, detail="asset_ids required when scope is 'selection'")

    status = await enqueue_dupe_scan(scope=body.scope, asset_ids=body.asset_ids)
    return RunDemoResponse(job_id=status.id)
