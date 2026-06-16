from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from photofant.config import get_data_root_base
from photofant.jobs.backup_job import enqueue_backup
from photofant.jobs.queue import JobStatus

router = APIRouter(prefix="/maintenance")


class BackupRequest(BaseModel):
    target_dir: str | None = None


class BackupResponse(BaseModel):
    job_id: str


class BackupInfo(BaseModel):
    filename: str
    path: str
    size: int
    created_at: str


def _default_backups_dir() -> Path:
    return get_data_root_base() / ".photofant" / "backups"


@router.post("/backup", response_model=BackupResponse)
async def trigger_backup(body: BackupRequest) -> BackupResponse:
    status: JobStatus = await enqueue_backup(body.target_dir)
    return BackupResponse(job_id=status.id)


@router.get("/backups", response_model=list[BackupInfo])
async def list_backups() -> list[BackupInfo]:
    backup_dir = _default_backups_dir()
    if not backup_dir.exists():
        return []

    results: list[BackupInfo] = []
    for file_path in sorted(backup_dir.glob("db-backup-*.sqlite"), reverse=True):
        stat = file_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime, tz=UTC).isoformat()
        results.append(BackupInfo(
            filename=file_path.name,
            path=str(file_path),
            size=stat.st_size,
            created_at=created_at,
        ))
    return results
