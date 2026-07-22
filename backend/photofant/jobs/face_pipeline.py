"""Deferred face-job scheduling.

FACE detection must run *after* both TAGGING and CAPTIONING complete for the
same asset (ordering constraint from queue.py).  With dedicated TAGGING and
CAPTIONING workers running in parallel, the priority-queue ordering alone is
no longer sufficient.  This module tracks per-asset prerequisites and enqueues
the FACE job exactly once, from whichever thread signals last.

Usage
-----
At pipeline start (import_job._enqueue_pipeline):
    face_pipeline.register(asset_id, prereq_count)

At the end of each prerequisite job (_run_tagging, _run_caption_with_preset) —
in a `finally`, so a failed prerequisite can never strand the face job:
    face_pipeline.signal(asset_id)

When prereq_count signals have arrived, FACE is enqueued automatically.
"""
from __future__ import annotations

import asyncio
import logging
import threading

log = logging.getLogger(__name__)


class FacePipeline:
    """Thread-safe tracker that enqueues a FACE job once all prerequisites complete."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # asset_id -> remaining_prerequisites
        self._pending: dict[int, int] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the running event loop so signals from worker threads can schedule coroutines."""
        self._loop = loop

    def register(self, asset_id: int, prereq_count: int) -> None:
        """Register an asset with N prerequisites before FACE may run.

        If prereq_count is 0 (no TAGGING or CAPTIONING configured), FACE is
        scheduled immediately.
        """
        if prereq_count <= 0:
            self._schedule_face(asset_id)
            return
        with self._lock:
            self._pending[asset_id] = prereq_count

    def signal(self, asset_id: int) -> None:
        """Mark one prerequisite as complete for *asset_id*.

        Thread-safe; may be called from any worker thread.  If all prerequisites
        are now satisfied the FACE job is enqueued automatically.  If the asset
        is not registered (e.g. auto_face=False or rerun path) the call is a
        no-op.
        """
        ready = False
        with self._lock:
            remaining = self._pending.get(asset_id)
            if remaining is None:
                return
            remaining -= 1
            if remaining <= 0:
                del self._pending[asset_id]
                ready = True
            else:
                self._pending[asset_id] = remaining

        if ready:
            self._schedule_face(asset_id)

    def _schedule_face(self, asset_id: int) -> None:
        if self._loop is None:
            log.warning(
                "FacePipeline: event loop not set — cannot enqueue FACE for asset %d", asset_id
            )
            return
        from photofant.jobs.face_job import enqueue_face

        asyncio.run_coroutine_threadsafe(enqueue_face(asset_id), self._loop)
        log.debug("FacePipeline: FACE enqueued for asset %d", asset_id)


face_pipeline = FacePipeline()
