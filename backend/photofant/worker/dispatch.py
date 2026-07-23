"""Dispatch-Tabelle des Worker-Prozesses: JobKind → Handler.

Eine Zeile pro migriertem Job — Phase 1 nur DEMO als Beweis-Fall, Phase 2/3 ergänzen den
Rest (CAPTIONING, TAGGING, EMBEDDING, HEURISTICS, CLASSIFICATION, FACE, CLUSTERING,
DUPE_SCAN).
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue


async def _demo_handler(status: JobStatus, _payload: dict[str, Any]) -> None:
    """Fünf Schritte à 1 Sekunde — beweist den IPC-Rundlauf ohne echte Inferenz.

    Ruft `job_queue.update()` wie jeder bestehende Job-Handler auch — `job_queue` ist hier
    die Worker-lokale `JobQueue`-Instanz (dasselbe Modul, frisch importiert im Kindprozess,
    siehe worker/process.py), ihre `_notify()`-Kette speist den Status-Forwarder.
    """
    steps = 5
    for step in range(1, steps + 1):
        await asyncio.sleep(1.0)
        job_queue.update(status, progress=step / steps, state=JobState.RUNNING)


JobHandler = Callable[[JobStatus, dict[str, Any]], Coroutine[Any, Any, None]]

JOB_HANDLERS: dict[JobKind, JobHandler] = {
    JobKind.DEMO: _demo_handler,
}
