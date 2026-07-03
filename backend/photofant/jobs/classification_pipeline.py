"""Deferred classification-job scheduling.

CLASSIFICATION needs both TAGGING (WD14 tag scores) and EMBEDDING (CLIP
image_embedding) to have written their result before it runs — but with
dedicated per-kind queues, either can finish first. This module tracks
per-asset prerequisites and enqueues CLASSIFICATION exactly once, from
whichever thread signals last. Mirrors `jobs/face_pipeline.py`.

Usage
-----
At pipeline start (import_job._enqueue_pipeline):
    classification_pipeline.register(asset_id, prereq_count)

At the end of each prerequisite job (_run_tagging, _run_embedding):
    classification_pipeline.signal(asset_id)
"""
from __future__ import annotations

import asyncio
import logging
import threading

log = logging.getLogger(__name__)


class ClassificationPipeline:
    """Thread-safe tracker that enqueues CLASSIFICATION once all prerequisites complete."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: dict[int, int] = {}  # asset_id -> remaining prerequisites
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the running event loop so signals from worker threads can schedule coroutines."""
        self._loop = loop

    def register(self, asset_id: int, prereq_count: int) -> None:
        """Register an asset with N prerequisites before CLASSIFICATION may run.

        If prereq_count is 0 (neither TAGGING nor EMBEDDING configured),
        CLASSIFICATION is scheduled immediately.
        """
        if prereq_count <= 0:
            self._schedule(asset_id)
            return
        with self._lock:
            self._pending[asset_id] = prereq_count

    def signal(self, asset_id: int) -> None:
        """Mark one prerequisite as complete for *asset_id*.

        Thread-safe; may be called from any worker thread. No-op if the asset
        is not registered (e.g. rerun path, which calls classification directly).
        """
        should_schedule = False
        with self._lock:
            remaining = self._pending.get(asset_id)
            if remaining is None:
                return
            remaining -= 1
            if remaining <= 0:
                del self._pending[asset_id]
                should_schedule = True
            else:
                self._pending[asset_id] = remaining

        if should_schedule:
            self._schedule(asset_id)

    def _schedule(self, asset_id: int) -> None:
        if self._loop is None:
            log.warning(
                "ClassificationPipeline: event loop not set — cannot enqueue for asset %d", asset_id
            )
            return
        from photofant.jobs.classification_job import enqueue_classification

        asyncio.run_coroutine_threadsafe(enqueue_classification(asset_id), self._loop)
        log.debug("ClassificationPipeline: CLASSIFICATION enqueued for asset %d", asset_id)


classification_pipeline = ClassificationPipeline()
