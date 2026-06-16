from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from photofant.config import get_data_root_base
from photofant.db.engine import get_db_path
from photofant.jobs.queue import JobKind, JobStatus, job_queue

log = logging.getLogger(__name__)


def _backup_dir(target_dir: str | None) -> Path:
    directory = Path(target_dir) if target_dir else get_data_root_base() / ".photofant" / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")


def _run_backup(db_path: Path, dest_path: Path) -> None:
    """SQLite Online Backup API — consistent snapshot even while DB is open."""
    source = sqlite3.connect(str(db_path))
    dest = sqlite3.connect(str(dest_path))
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()


async def run_backup_job(status: JobStatus, target_dir: str | None) -> None:
    db_path = get_db_path()
    directory = _backup_dir(target_dir)
    dest_path = directory / f"db-backup-{_timestamp()}.sqlite"
    await asyncio.to_thread(_run_backup, db_path, dest_path)
    log.info("Backup created: %s (%d bytes)", dest_path, dest_path.stat().st_size)


async def enqueue_backup(target_dir: str | None = None) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.BACKUP,
        label="DB-Backup",
        coro_factory=lambda job_status: run_backup_job(job_status, target_dir),
    )
