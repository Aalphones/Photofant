"""Live pool resizing for tagging/captioning workers (no process restart)."""
from __future__ import annotations

import asyncio

import pytest

from photofant.jobs.queue import JobKind, JobQueue


@pytest.fixture
def job_queue() -> JobQueue:
    return JobQueue()


async def _run_forever_until_cancelled(status: object) -> None:
    await asyncio.sleep(3600)


async def test_scale_up_spawns_additional_workers(job_queue: JobQueue) -> None:
    job_queue._scale_pool(
        job_queue._tagging_worker_tasks, job_queue._tagging_queue, job_queue._tagging_worker, 1
    )
    assert len(job_queue._tagging_worker_tasks) == 1

    job_queue._scale_pool(
        job_queue._tagging_worker_tasks, job_queue._tagging_queue, job_queue._tagging_worker, 4
    )
    await asyncio.sleep(0)  # let the new tasks actually start
    assert len(job_queue._tagging_worker_tasks) == 4

    await job_queue.stop()


async def test_scale_down_only_removes_idle_workers(job_queue: JobQueue) -> None:
    job_queue._scale_pool(
        job_queue._captioning_worker_tasks, job_queue._captioning_queue, job_queue._captioning_worker, 4
    )
    await asyncio.sleep(0)
    assert len(job_queue._captioning_worker_tasks) == 4

    job_queue._scale_pool(
        job_queue._captioning_worker_tasks, job_queue._captioning_queue, job_queue._captioning_worker, 1
    )
    await asyncio.sleep(0.05)  # give the poison-pilled workers a tick to exit
    assert len(job_queue._captioning_worker_tasks) == 1

    await job_queue.stop()


async def test_scale_down_does_not_interrupt_a_running_job(job_queue: JobQueue) -> None:
    job_queue._scale_pool(
        job_queue._tagging_worker_tasks, job_queue._tagging_queue, job_queue._tagging_worker, 2
    )
    await asyncio.sleep(0)

    status = await job_queue.enqueue(JobKind.TAGGING, "long job", _run_forever_until_cancelled)
    await asyncio.sleep(0.05)  # let a worker pick it up

    # Shrinking to 1 must not cancel the worker that's mid-job — only the idle one exits.
    job_queue._scale_pool(
        job_queue._tagging_worker_tasks, job_queue._tagging_queue, job_queue._tagging_worker, 1
    )
    await asyncio.sleep(0.05)

    assert len(job_queue._tagging_worker_tasks) == 1
    assert status.state.value == "running"

    await job_queue.stop()
