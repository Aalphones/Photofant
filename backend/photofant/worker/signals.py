"""Cross-process pipeline-signal emission (ADR-037).

Jobs that end with `face_pipeline.signal()`/`classification_pipeline.signal()` run in two
different process contexts depending on the caller:
- Normal path (import pipeline, queued TAGGING/CAPTIONING): runs in the worker process since
  Phase 2 — the real `face_pipeline`/`classification_pipeline` singletons that track the
  asset's registered prerequisite count live in the API process, so the signal must cross the
  IPC boundary.
- Direct path (`rerun_job.py` awaits the remote job but never calls `register()` for it) —
  still ends up in the worker process, so the same IPC path applies; the API-side singleton
  simply no-ops the signal since the asset was never registered (unchanged pre-existing
  behaviour, see `classification_pipeline.py` docstring).

`emit_pipeline_signal()` picks the right path automatically via a module-global handle set
once at worker startup (analogous to `face_pipeline.set_loop()`) — call sites in
`caption_job.py`/`tagging_job.py` don't need to know which process they run in. If no handle
is set (e.g. code executed directly in the API process, outside the worker), it falls back
to calling the local singleton directly instead of dropping the signal.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import multiprocessing as mp

    from photofant.worker.protocol import WorkerStatusMessage

log = logging.getLogger(__name__)

_status_queue: mp.Queue[WorkerStatusMessage] | None = None


def set_status_queue(status_queue: mp.Queue[WorkerStatusMessage]) -> None:
    """Marks 'we're running in the worker process' — called once at worker startup."""
    global _status_queue
    _status_queue = status_queue


def emit_pipeline_signal(pipeline: Literal["face", "classification"], asset_id: int) -> None:
    if _status_queue is not None:
        from photofant.worker.protocol import PipelineSignalMessage

        _status_queue.put(PipelineSignalMessage(type="pipeline_signal", pipeline=pipeline, asset_id=asset_id))
        return

    # No worker handle set — we're running directly in the API process (no IPC needed).
    if pipeline == "face":
        from photofant.jobs.face_pipeline import face_pipeline

        face_pipeline.signal(asset_id)
    else:
        from photofant.jobs.classification_pipeline import classification_pipeline

        classification_pipeline.signal(asset_id)
