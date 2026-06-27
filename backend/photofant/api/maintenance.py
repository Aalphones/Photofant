from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.config import get_data_root, get_data_root_base
from photofant.db.cache import count_thumbnail_targets, get_cache_db_path
from photofant.db.engine import get_db_path
from photofant.db.session import get_session
from photofant.jobs.backup_job import enqueue_backup
from photofant.jobs.import_job import enqueue_import
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.jobs.rebuild_job import RebuildTarget, enqueue_rebuild
from photofant.jobs.reconcile_job import enqueue_reconcile
from photofant.jobs.thumbnail_job import enqueue_thumbnail_rebuild
from photofant.maintenance import repair
from photofant.maintenance.store import load_report

router = APIRouter(prefix="/maintenance")

DbSession = Annotated[Session, Depends(get_session)]


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


# ── Reconcile (FS↔DB) ────────────────────────────────────────────────────────


class JobResponse(BaseModel):
    job_id: str


class OrphanDto(BaseModel):
    path: str
    size: int
    person_name: str | None
    detail: str


class MissingDto(BaseModel):
    instance_id: int
    asset_id: int
    path: str
    person_name: str | None
    detail: str


class DriftDto(BaseModel):
    instance_id: int
    asset_id: int
    db_path: str
    found_path: str
    person_name: str | None
    detail: str


class OrphanedFaceDto(BaseModel):
    face_id: int
    asset_id: int
    crop_path: str
    person_name: str | None
    detail: str


class MisassignedInstanceDto(BaseModel):
    instance_id: int
    asset_id: int
    path: str
    person_name: str | None
    detail: str


class AcknowledgedMissingDto(BaseModel):
    instance_id: int
    asset_id: int
    path: str
    person_name: str | None
    missing_at: str
    detail: str


class ReconcileReportDto(BaseModel):
    generated_at: str | None
    orphaned_files: list[OrphanDto]
    missing_files: list[MissingDto]
    path_drift: list[DriftDto]
    orphaned_faces: list[OrphanedFaceDto] = []
    misassigned_instances: list[MisassignedInstanceDto] = []
    acknowledged_missing: list[AcknowledgedMissingDto] = []


_EMPTY_REPORT = ReconcileReportDto(
    generated_at=None,
    orphaned_files=[],
    missing_files=[],
    path_drift=[],
    orphaned_faces=[],
    misassigned_instances=[],
    acknowledged_missing=[],
)


class RepairItem(BaseModel):
    kind: Literal[
        "orphan", "missing", "drift", "orphaned_face", "misassigned", "acknowledged_missing"
    ]
    instance_id: int | None = None
    face_id: int | None = None
    path: str | None = None
    found_path: str | None = None


class RepairActionDto(BaseModel):
    item: RepairItem
    action: Literal["index", "mark_missing", "trash", "fix_path", "purge", "fix_assignment"]


class RepairRequest(BaseModel):
    actions: list[RepairActionDto]


class RepairResultDto(BaseModel):
    kind: str
    action: str
    status: Literal["ok", "error"]
    message: str | None = None


class RepairResponse(BaseModel):
    results: list[RepairResultDto]
    import_job_id: str | None = None


@router.post("/reconcile", response_model=JobResponse)
async def trigger_reconcile() -> JobResponse:
    status: JobStatus = await enqueue_reconcile()
    return JobResponse(job_id=status.id)


@router.get("/reconcile/report", response_model=ReconcileReportDto)
async def get_reconcile_report(session: DbSession) -> ReconcileReportDto:
    report = load_report(session)
    if report is None:
        return _EMPTY_REPORT
    return ReconcileReportDto(**report)


async def _apply_one(
    session: Session,
    entry: RepairActionDto,
    data_root: Path,
    import_paths: list[str],
) -> RepairResultDto:
    item = entry.item
    action = entry.action

    if item.kind == "orphan" and action == "index":
        if not item.path:
            raise repair.RepairError("orphan index requires a path")
        repair.ensure_under_root(Path(item.path), data_root)
        import_paths.append(item.path)
    elif item.kind == "orphan" and action == "trash":
        if not item.path:
            raise repair.RepairError("orphan trash requires a path")
        await repair.trash_orphan(session, item.path, data_root)
    elif item.kind == "missing" and action == "mark_missing":
        if item.instance_id is None:
            raise repair.RepairError("mark_missing requires an instance_id")
        repair.mark_missing(session, item.instance_id)
    elif item.kind == "missing" and action == "trash":
        if item.instance_id is None:
            raise repair.RepairError("missing trash requires an instance_id")
        await repair.purge_missing(session, item.instance_id, get_cache_db_path())
    elif item.kind == "drift" and action == "fix_path":
        if item.instance_id is None or not item.found_path:
            raise repair.RepairError("fix_path requires instance_id and found_path")
        repair.fix_drift(session, item.instance_id, item.found_path, data_root)
    elif item.kind == "orphaned_face" and action == "purge":
        if item.face_id is None:
            raise repair.RepairError("orphaned_face purge requires a face_id")
        await repair.purge_orphaned_face(session, item.face_id, get_cache_db_path())
    elif item.kind == "misassigned" and action == "fix_assignment":
        if item.instance_id is None:
            raise repair.RepairError("fix_assignment requires an instance_id")
        repair.fix_misassigned(session, item.instance_id, data_root)
    elif item.kind == "acknowledged_missing" and action == "purge":
        if item.instance_id is None:
            raise repair.RepairError("acknowledged_missing purge requires an instance_id")
        await repair.purge_missing(session, item.instance_id, get_cache_db_path())
    else:
        raise repair.RepairError(f"unsupported action '{action}' for kind '{item.kind}'")

    return RepairResultDto(kind=item.kind, action=action, status="ok")


@router.post("/reconcile/repair", response_model=RepairResponse)
async def repair_reconcile(body: RepairRequest, session: DbSession) -> RepairResponse:
    data_root = get_data_root()
    import_paths: list[str] = []
    results: list[RepairResultDto] = []

    for entry in body.actions:
        try:
            results.append(await _apply_one(session, entry, data_root, import_paths))
        except repair.RepairError as exc:
            results.append(
                RepairResultDto(kind=entry.item.kind, action=entry.action, status="error", message=str(exc))
            )

    import_job_id: str | None = None
    if import_paths:
        import_status = await enqueue_import(import_paths)
        import_job_id = import_status.id

    return RepairResponse(results=results, import_job_id=import_job_id)


# ── Rebuild (Cache) ───────────────────────────────────────────────────────────


class RebuildRequest(BaseModel):
    target: RebuildTarget


@router.post("/rebuild", response_model=JobResponse)
async def trigger_rebuild(body: RebuildRequest) -> JobResponse:
    status: JobStatus = await enqueue_rebuild(body.target)
    return JobResponse(job_id=status.id)


@router.post("/rebuild-thumbnails", response_model=JobResponse)
async def trigger_thumbnail_rebuild() -> JobResponse:
    already_running = any(
        job.kind == JobKind.THUMBNAIL_REBUILD and job.state in (JobState.QUEUED, JobState.RUNNING)
        for job in job_queue.snapshot()
    )
    if already_running:
        raise HTTPException(status_code=409, detail="Thumbnail-Rebuild läuft bereits")
    status: JobStatus = await enqueue_thumbnail_rebuild()
    return JobResponse(job_id=status.id)


# ── Status ────────────────────────────────────────────────────────────────────


class MaintenanceStatusDto(BaseModel):
    db_size: int            # db.sqlite size in bytes
    thumbnail_count: int    # assets with at least one cached thumbnail
    cache_size: int         # thumbnails.sqlite size in bytes


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


@router.get("/status", response_model=MaintenanceStatusDto)
async def get_status() -> MaintenanceStatusDto:
    cache_path = get_cache_db_path()
    return MaintenanceStatusDto(
        db_size=_file_size(get_db_path()),
        thumbnail_count=count_thumbnail_targets(cache_path),
        cache_size=_file_size(cache_path),
    )
