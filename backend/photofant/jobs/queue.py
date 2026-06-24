from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

log = logging.getLogger(__name__)


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class JobKind(StrEnum):
    DEMO = "demo"
    IMPORT = "import"
    SCAN = "scan"
    THUMBNAIL = "thumbnail"
    BACKUP = "backup"
    RECONCILE = "reconcile"
    REBUILD = "rebuild"
    THUMBNAIL_REBUILD = "thumbnail_rebuild"
    DOWNLOAD = "download_model"
    TAGGING = "tagging"
    CAPTIONING = "captioning"
    EMBEDDING = "embedding"
    HEURISTICS = "heuristics"
    RERUN = "rerun"
    REEVALUATE = "reevaluate"
    DUPE_SCAN = "dupe_scan"
    FACE = "face"
    CLUSTERING = "clustering"
    BULK_EDIT = "bulk_edit"
    COMFYUI_RUN = "comfyui_run"
    INSTALL_GENERATIVE = "install_generative"
    UPSCALE = "upscale"
    FLUX_EDIT = "flux_edit"
    INPAINT = "inpaint"


@dataclass
class JobStatus:
    id: str
    kind: JobKind
    label: str
    progress: float = 0.0
    state: JobState = JobState.QUEUED
    error: str | None = None


CoroFactory = Callable[["JobStatus"], Coroutine[Any, Any, None]]

# Job kinds that bypass the sequential queue and run as independent concurrent tasks.
# Add a kind here when it is I/O-bound and must never block other queue entries.
_PARALLEL_KINDS: frozenset[JobKind] = frozenset({JobKind.DOWNLOAD})


@dataclass
class _Job:
    status: JobStatus
    coro_factory: CoroFactory


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[_Job] = asyncio.Queue()
        self._jobs: dict[str, JobStatus] = {}
        self._subscribers: list[asyncio.Queue[JobStatus]] = []
        self._worker_task: asyncio.Task[None] | None = None
        self._parallel_tasks: set[asyncio.Task[None]] = set()

    def start(self) -> None:
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
        for task in list(self._parallel_tasks):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def subscribe(self) -> asyncio.Queue[JobStatus]:
        queue: asyncio.Queue[JobStatus] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[JobStatus]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def snapshot(self) -> list[JobStatus]:
        return list(self._jobs.values())

    async def enqueue(self, kind: JobKind, label: str, coro_factory: CoroFactory) -> JobStatus:
        job_id = str(uuid.uuid4())
        status = JobStatus(id=job_id, kind=kind, label=label)
        self._jobs[job_id] = status
        self._notify(status)
        if kind in _PARALLEL_KINDS:
            task = asyncio.create_task(self._run_parallel(status, coro_factory))
            self._parallel_tasks.add(task)
            task.add_done_callback(self._parallel_tasks.discard)
        else:
            await self._queue.put(_Job(status=status, coro_factory=coro_factory))
        return status

    def update(self, status: JobStatus, progress: float, state: JobState, error: str | None = None) -> None:
        status.progress = progress
        status.state = state
        status.error = error
        self._notify(status)

    def _notify(self, status: JobStatus) -> None:
        for subscriber in self._subscribers:
            subscriber.put_nowait(status)

    async def _run_parallel(self, status: JobStatus, coro_factory: CoroFactory) -> None:
        self.update(status, progress=0.0, state=JobState.RUNNING)
        try:
            await coro_factory(status)
            self.update(status, progress=1.0, state=JobState.DONE)
        except Exception as exc:
            log.exception("Parallel job %s failed", status.id)
            self.update(status, progress=status.progress, state=JobState.ERROR, error=str(exc))

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            status = job.status
            self.update(status, progress=0.0, state=JobState.RUNNING)
            try:
                await job.coro_factory(status)
                self.update(status, progress=1.0, state=JobState.DONE)
            except Exception as exc:
                log.exception("Job %s failed", status.id)
                self.update(status, progress=status.progress, state=JobState.ERROR, error=str(exc))
            finally:
                self._queue.task_done()


job_queue = JobQueue()
