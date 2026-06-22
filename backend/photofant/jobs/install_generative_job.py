"""Install the optional generative dependency group (torch, diffusers, etc.).

Triggered via the Settings UI when the user wants to enable generative features.
Runs `uv pip install` in a subprocess so the backend stays responsive.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from photofant.inference.generative_engine import GenerativeAvailability, check_generative_available
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

_PYPROJECT_DIR = Path(__file__).parent.parent.parent


async def _run_install(status: JobStatus) -> None:
    """Run uv pip install photofant[generative] as a subprocess."""
    availability = check_generative_available()
    if availability is GenerativeAvailability.AVAILABLE:
        log.info("Generative dependencies already installed — skipping")
        job_queue.update(status, progress=1.0, state=JobState.DONE)
        return

    log.info("Installing generative dependency group...")
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)

    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "uv", "pip", "install",
        "--quiet",
        f"{_PYPROJECT_DIR}[generative]",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode(errors="replace").strip()
        log.error("Generative install failed (exit %d): %s", process.returncode, error_msg)
        raise RuntimeError(
            f"Installation fehlgeschlagen (Exit-Code {process.returncode}). "
            f"Details: {error_msg[:500]}"
        )

    log.info("Generative dependencies installed successfully")
    job_queue.update(status, progress=0.9, state=JobState.RUNNING)

    post_check = check_generative_available()
    if post_check is not GenerativeAvailability.AVAILABLE:
        raise RuntimeError(
            "Installation abgeschlossen, aber torch/diffusers lassen sich nicht importieren. "
            "Möglicherweise fehlt eine CUDA-kompatible torch-Version für diese GPU."
        )


async def enqueue_install_generative() -> JobStatus:
    """Enqueue the generative install job."""
    return await job_queue.enqueue(
        JobKind.INSTALL_GENERATIVE,
        "Generative Abhängigkeiten installieren (torch, diffusers, …)",
        _run_install,
    )
