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
    CLASSIFICATION = "classification"
    RERUN = "rerun"
    REEVALUATE = "reevaluate"
    DUPE_SCAN = "dupe_scan"
    FACE = "face"
    CLUSTERING = "clustering"
    BULK_EDIT = "bulk_edit"
    BULK_ASSIGN = "bulk_assign"
    COMFYUI_RUN = "comfyui_run"
    EXPORT = "export"
    CAPTIONS = "captions"
    KNOWLEDGE_LOOKUP = "knowledge_lookup"


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

# Background-inference kinds run on a dedicated worker so user-triggered jobs on the
# main worker (import, export, ComfyUI) never wait behind a slow caption run.
# Lower number = higher priority; FIFO within the same priority via a sequence counter.
#
# ORDERING CONSTRAINT: FACE must run *after* HEURISTICS, EMBEDDING, TAGGING and
# CAPTIONING for the same asset complete.
# Reason: FACE calls run_incremental_match → materialize_assignment which physically
# moves the file to the matched person's folder, invalidating any stale asset_path
# closures still waiting in the queue.
#
# With dedicated TAGGING and CAPTIONING workers (separate queues, see below) the
# priority-queue order alone cannot enforce this — face_pipeline.py handles it
# instead: FACE is enqueued *only* after both dedicated workers signal completion.
_BACKGROUND_PRIORITY: dict[JobKind, int] = {
    JobKind.COMFYUI_RUN: 10,
    JobKind.HEURISTICS: 20,
    JobKind.EMBEDDING: 30,
    JobKind.CLASSIFICATION: 35,
    JobKind.FACE: 45,
    JobKind.CLUSTERING: 50,
    JobKind.DUPE_SCAN: 50,
}

_BACKGROUND_KINDS: frozenset[JobKind] = frozenset(_BACKGROUND_PRIORITY)

# TAGGING (WD14) and CAPTIONING (Florence-2/Qwen/JoyCaption) each run on their own
# dedicated worker so they can overlap on the GPU without sharing an ONNX session.
# Two different InferenceSessions (different model files) are safe to run concurrently;
# two threads sharing the *same* session are not (ONNX Runtime is not re-entrant).
_TAGGING_KINDS: frozenset[JobKind] = frozenset({JobKind.TAGGING})
_CAPTIONING_KINDS: frozenset[JobKind] = frozenset({JobKind.CAPTIONING})


@dataclass
class _Job:
    status: JobStatus
    coro_factory: CoroFactory


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[_Job] = asyncio.Queue()
        self._background_queue: asyncio.PriorityQueue[tuple[int, int, _Job]] = asyncio.PriorityQueue()
        # `None` is a poison pill: pushed by _scale_pool() to shrink a pool. Whichever
        # worker dequeues it exits — it never jumps ahead of real jobs already queued,
        # so shrinking never interrupts a job that's already running.
        self._tagging_queue: asyncio.Queue[_Job | None] = asyncio.Queue()
        self._captioning_queue: asyncio.Queue[_Job | None] = asyncio.Queue()
        self._bg_seq: int = 0
        self._jobs: dict[str, JobStatus] = {}
        self._subscribers: list[asyncio.Queue[JobStatus]] = []
        self._worker_task: asyncio.Task[None] | None = None
        self._background_worker_task: asyncio.Task[None] | None = None
        self._tagging_worker_tasks: set[asyncio.Task[None]] = set()
        self._captioning_worker_tasks: set[asyncio.Task[None]] = set()
        self._parallel_tasks: set[asyncio.Task[None]] = set()

    def start(self) -> None:
        from photofant.jobs.classification_pipeline import classification_pipeline
        from photofant.jobs.face_pipeline import face_pipeline
        from photofant.settings import load_settings

        settings = load_settings()
        face_pipeline.set_loop(asyncio.get_running_loop())
        classification_pipeline.set_loop(asyncio.get_running_loop())
        self._worker_task = asyncio.create_task(self._worker())
        self._background_worker_task = asyncio.create_task(self._background_worker())
        self._scale_pool(
            self._tagging_worker_tasks, self._tagging_queue, self._tagging_worker, settings["tagging_workers"]
        )
        self._scale_pool(
            self._captioning_worker_tasks,
            self._captioning_queue,
            self._captioning_worker,
            settings["captioning_workers"],
        )

    def resize_tagging_workers(self, target: int) -> None:
        """Grow/shrink the tagging pool to `target` workers without a process restart."""
        self._scale_pool(self._tagging_worker_tasks, self._tagging_queue, self._tagging_worker, target)

    def resize_captioning_workers(self, target: int) -> None:
        """Grow/shrink the captioning pool to `target` workers without a process restart."""
        self._scale_pool(self._captioning_worker_tasks, self._captioning_queue, self._captioning_worker, target)

    def _scale_pool(
        self,
        tasks: set[asyncio.Task[None]],
        queue: asyncio.Queue[_Job | None],
        spawn_worker: Callable[[], Coroutine[Any, Any, None]],
        target: int,
    ) -> None:
        target = max(0, target)
        current = len(tasks)
        if target > current:
            for _ in range(target - current):
                task = asyncio.create_task(spawn_worker())
                tasks.add(task)
                task.add_done_callback(tasks.discard)
        elif target < current:
            # Wake exactly the surplus count of idle workers via poison pills; a worker
            # stuck mid-job is never touched since it only checks the queue between jobs.
            for _ in range(current - target):
                queue.put_nowait(None)

    async def stop(self) -> None:
        singleton_worker_tasks = (self._worker_task, self._background_worker_task)
        for worker_task in singleton_worker_tasks:
            if worker_task:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task
        for pool_task in (*self._tagging_worker_tasks, *self._captioning_worker_tasks):
            pool_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pool_task
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
        job = _Job(status=status, coro_factory=coro_factory)
        if kind in _PARALLEL_KINDS:
            task = asyncio.create_task(self._run_job(status, coro_factory))
            self._parallel_tasks.add(task)
            task.add_done_callback(self._parallel_tasks.discard)
        elif kind in _TAGGING_KINDS:
            await self._tagging_queue.put(job)
        elif kind in _CAPTIONING_KINDS:
            await self._captioning_queue.put(job)
        elif kind in _BACKGROUND_KINDS:
            self._bg_seq += 1
            await self._background_queue.put((_BACKGROUND_PRIORITY[kind], self._bg_seq, job))
        else:
            await self._queue.put(job)
        return status

    def update(self, status: JobStatus, progress: float, state: JobState, error: str | None = None) -> None:
        status.progress = progress
        status.state = state
        status.error = error
        self._notify(status)

    def _notify(self, status: JobStatus) -> None:
        for subscriber in self._subscribers:
            subscriber.put_nowait(status)

    async def _run_job(self, status: JobStatus, coro_factory: CoroFactory) -> None:
        self.update(status, progress=0.0, state=JobState.RUNNING)
        try:
            await coro_factory(status)
            self.update(status, progress=1.0, state=JobState.DONE)
        except Exception as exc:
            log.exception("Job %s failed", status.id)
            self.update(status, progress=status.progress, state=JobState.ERROR, error=str(exc))

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._run_job(job.status, job.coro_factory)
            finally:
                self._queue.task_done()

    async def _background_worker(self) -> None:
        while True:
            _priority, _seq, job = await self._background_queue.get()
            try:
                await self._run_job(job.status, job.coro_factory)
            finally:
                self._background_queue.task_done()

    async def _tagging_worker(self) -> None:
        while True:
            job = await self._tagging_queue.get()
            try:
                if job is None:  # poison pill from _scale_pool() — shrink by one
                    return
                await self._run_job(job.status, job.coro_factory)
            finally:
                self._tagging_queue.task_done()

    async def _captioning_worker(self) -> None:
        while True:
            job = await self._captioning_queue.get()
            try:
                if job is None:  # poison pill from _scale_pool() — shrink by one
                    return
                await self._run_job(job.status, job.coro_factory)
            finally:
                self._captioning_queue.task_done()


job_queue = JobQueue()
