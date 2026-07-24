"""Worker-Prozess-Entry-Point — läuft in einem eigenen OS-Prozess (multiprocessing.Process),
NICHT im API-Prozess. Bekommt zwei multiprocessing.Queue-Objekte beim Start übergeben und
startet darin sein eigenes asyncio-Event-Loop.

WICHTIG (Windows `spawn`): Diese Funktion ist der komplette Eintrittspunkt des Kindprozesses —
sie darf keine Seiteneffekte voraussetzen, die nur im API-Prozess passiert sind (z.B. FastAPI-
App-Erzeugung). Alle Imports hier sind kindprozess-lokal und frisch (siehe ADR-037).

`job_queue` (aus `photofant.jobs.queue`) ist ein Modul-Level-Singleton — im Kindprozess ist das
eine eigene, vom API-Prozess komplett unabhängige Instanz (Windows `spawn` importiert alle
Module frisch). Handler in `dispatch.py` rufen `job_queue.update()`/`.set_result()` exakt wie
jeder bestehende Job-Handler auch — kein Sonderfall nötig, wenn diese Jobs ab Phase 2/3
migrieren.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from photofant.jobs.queue import JobKind, JobQueue, JobStatus, job_queue
from photofant.worker import signals
from photofant.worker.dispatch import JOB_HANDLERS, JobHandler
from photofant.worker.protocol import JobRequest, JobStatusMessage

if TYPE_CHECKING:
    import multiprocessing as mp

    from photofant.worker.protocol import WorkerStatusMessage

log = logging.getLogger(__name__)

IDLE_EVICTION_INTERVAL_SECONDS: float = 60.0


async def _idle_eviction_loop() -> None:
    """Räumt ONNX-/Torch-/GGUF-Modelle auf, die im Worker-Prozess idle geworden sind.

    Gegenstück zu `main.py::_idle_eviction_loop` im API-Prozess. Seit ADR-037 Phase 2 laufen
    CAPTIONING (Florence-2/JoyCaption/Qwen2.5-VL) und TAGGING (WD14) hier im Worker-Prozess —
    wegen Windows `spawn` sind `session_manager`/`generative_engine`/`gguf_engine` hier eigene
    Instanzen, getrennt von denen im API-Prozess. Ohne diese Schleife bleiben ihre Modelle bis
    zum Prozess-Ende im VRAM, weil niemand `evict_idle()` aufruft. Volle Migration der Schleife
    (inkl. Entfernen aus `main.py`) ist für Phase 3 vorgesehen, sobald auch die restlichen
    Modell-Jobs hierher umziehen — dieser Vorgriff schließt die Lücke schon für die zwei
    bereits migrierten Job-Arten.
    """
    from photofant.inference.generative_engine import generative_engine
    from photofant.inference.gguf_engine import gguf_engine
    from photofant.inference.session_manager import session_manager
    from photofant.settings import load_settings

    while True:
        await asyncio.sleep(IDLE_EVICTION_INTERVAL_SECONDS)
        session_manager.evict_idle()
        ai_idle_timeout = load_settings()["ai"]["idleTimeoutSeconds"]
        generative_engine.evict_idle(ai_idle_timeout)
        gguf_engine.evict_idle(ai_idle_timeout)


def _bind_handler(handler: JobHandler, payload: dict[str, Any]) -> Callable[[JobStatus], Coroutine[Any, Any, None]]:
    """Bindet Handler + Payload zu einem `CoroFactory` — vermeidet ein Late-Binding-Closure-Problem
    (der Loop unten erzeugt pro Request einen neuen Aufruf, bevor der vorherige garantiert
    ausgeführt wurde) und ist für mypy eindeutig typisierbar, anders als eine Default-Arg-Lambda.
    """

    async def _coro(status: JobStatus) -> None:
        await handler(status, payload)

    return _coro


async def _request_listener(worker_queue: JobQueue, request_queue: mp.Queue[JobRequest | None]) -> None:
    loop = asyncio.get_running_loop()
    while True:
        request = await loop.run_in_executor(None, request_queue.get)  # blocking get, im Executor-Thread
        if request is None:  # Poison Pill — sauberes Herunterfahren
            return
        kind = JobKind(request.kind)
        handler = JOB_HANDLERS.get(kind)
        if handler is None:
            log.error("Worker: kein Handler für JobKind %r — Auftrag verworfen", request.kind)
            continue
        await worker_queue.enqueue(
            kind=kind,
            label=request.label,
            coro_factory=_bind_handler(handler, request.payload),
            job_id=request.job_id,  # muss mit der API-seitig bereits angelegten JobStatus.id übereinstimmen
        )


async def _status_forwarder(worker_queue: JobQueue, status_queue: mp.Queue[WorkerStatusMessage]) -> None:
    subscriber = worker_queue.subscribe()
    while True:
        status = await subscriber.get()
        status_queue.put(
            JobStatusMessage(
                type="job_status",
                job_id=status.id,
                progress=status.progress,
                state=status.state.value,
                error=status.error,
                result=status.result,
            )
        )


async def _run_worker(
    request_queue: mp.Queue[JobRequest | None], status_queue: mp.Queue[WorkerStatusMessage]
) -> None:
    # Vor job_queue.start(): markiert für signals.py "wir laufen im Worker-Prozess" — jeder
    # emit_pipeline_signal()-Aufruf ab hier schreibt auf die IPC-Queue statt lokal zu signalisieren.
    signals.set_status_queue(status_queue)
    job_queue.start()
    log.info("Worker-Prozess bereit")
    forwarder_task = asyncio.create_task(_status_forwarder(job_queue, status_queue))
    eviction_task = asyncio.create_task(_idle_eviction_loop())
    try:
        await _request_listener(job_queue, request_queue)
    finally:
        eviction_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await eviction_task
        forwarder_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await forwarder_task
        await job_queue.stop()

        from photofant.inference.generative_engine import generative_engine
        from photofant.inference.gguf_engine import gguf_engine
        from photofant.inference.session_manager import session_manager

        generative_engine.unload()
        gguf_engine.unload()
        session_manager.shutdown()


def run_worker_process(
    request_queue: mp.Queue[JobRequest | None], status_queue: mp.Queue[WorkerStatusMessage]
) -> None:
    """Synchroner Einstiegspunkt für `multiprocessing.Process(target=...)`."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(_run_worker(request_queue, status_queue))
