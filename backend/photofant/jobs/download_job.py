"""Managed model download job — httpx streaming, Range-resume, SHA-256 verification.

This is the ONLY place in the application that performs network I/O at runtime
(Critical Rule 1: no network access elsewhere once models are active).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import zipfile
from pathlib import Path
from typing import TypedDict

import httpx
from sqlalchemy.orm import Session

from photofant.db.models import ModelRegistry
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.models.loader import ManifestEntry, get_manifest_entry, load_manifest

log = logging.getLogger(__name__)

_CHUNK_SIZE = 512 * 1024  # 512 KB per read
_HTTP_TIMEOUT = httpx.Timeout(connect=30.0, read=3600.0, write=60.0, pool=30.0)


class ScanResult(TypedDict):
    manifest_id: str
    path: str


# ---------------------------------------------------------------------------
# Blocking helpers — always run via asyncio.to_thread
# ---------------------------------------------------------------------------


def _compute_sha256(path: Path) -> str:
    """Compute SHA-256 of an existing file."""
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        while chunk := file_handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_zip(zip_path: Path, target_dir: Path) -> None:
    """Extract zip archive to target_dir then delete the archive."""
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zip_file:
        zip_file.extractall(target_dir)
    zip_path.unlink()
    log.info("Extracted %s → %s", zip_path.name, target_dir)


def _hf_snapshot_sync(hf_repo: str, local_dir: Path) -> None:
    """Download a HuggingFace repo snapshot to local_dir (blocking)."""
    from huggingface_hub import snapshot_download

    local_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=hf_repo,
        local_dir=str(local_dir),
        ignore_patterns=[
            "*.bin",
            "*.safetensors",
            "*.msgpack",
            "*.h5",
            "flax_model*",
            "tf_model*",
            "rust_model*",
        ],
    )
    log.info("HuggingFace snapshot: %s → %s", hf_repo, local_dir)


def _upsert_registry_row(
    session: Session,
    entry: ManifestEntry,
    model_path: str,
    managed: bool,
) -> None:
    """Insert or update a ModelRegistry row within an existing session (no commit)."""
    existing = session.query(ModelRegistry).filter(ModelRegistry.manifest_id == entry.id).first()
    if existing is not None:
        existing.path = model_path
        existing.managed = managed
        existing.enabled = True
        existing.capabilities = entry.capabilities
    else:
        row = ModelRegistry(
            manifest_id=entry.id,
            role=entry.role,
            name=entry.name,
            variant=entry.variant,
            format=entry.format,
            path=model_path,
            managed=managed,
            enabled=True,
            caption_mode=entry.caption_mode,
            capabilities=entry.capabilities,
        )
        session.add(row)
    log.info("Registered model %s at %s (managed=%s)", entry.id, model_path, managed)


def _register_model_in_db(manifest_id: str, entry: ManifestEntry, model_path: str) -> None:
    """Open a fresh session, upsert registry row, commit (blocking)."""
    with SessionLocal() as session:
        _upsert_registry_row(session, entry, model_path, managed=True)
        session.commit()


def scan_models_dir(models_dir: Path) -> list[ScanResult]:
    """Walk models_dir for files matching manifest entries; register found models.

    Uses SHA-256 if available in manifest; falls back to file-presence matching.
    Blocking — call via asyncio.to_thread in async context.
    """
    manifest_entries = load_manifest()
    registered: list[ScanResult] = []

    with SessionLocal() as session:
        for entry in manifest_entries:
            model_dir = models_dir / entry.id

            if entry.hf_repo:
                if model_dir.is_dir() and any(model_dir.iterdir()):
                    _upsert_registry_row(session, entry, str(model_dir), managed=True)
                    registered.append({"manifest_id": entry.id, "path": str(model_dir)})
                continue

            if entry.format == "onnx_bundle":
                if model_dir.is_dir() and any(model_dir.rglob("*.onnx")):
                    _upsert_registry_row(session, entry, str(model_dir), managed=True)
                    registered.append({"manifest_id": entry.id, "path": str(model_dir)})
                continue

            # Regular ONNX: check each expected file
            if not model_dir.is_dir():
                continue

            all_valid = True
            for file_info in entry.files:
                file_path = model_dir / file_info["filename"]
                if not file_path.is_file():
                    all_valid = False
                    break

                expected_sha256: str | None = file_info.get("sha256")
                if expected_sha256 is not None:
                    computed = _compute_sha256(file_path)
                    if computed != expected_sha256:
                        log.warning(
                            "SHA-256 mismatch for %s (expected %s…, got %s…) — skipping",
                            file_path, expected_sha256[:8], computed[:8],
                        )
                        all_valid = False
                        break
                else:
                    log.debug("No SHA-256 in manifest for %s — filename match only", file_info["filename"])

            if all_valid:
                _upsert_registry_row(session, entry, str(model_dir), managed=True)
                registered.append({"manifest_id": entry.id, "path": str(model_dir)})

        session.commit()

    log.info("Scan complete: %d model(s) registered", len(registered))
    return registered


# ---------------------------------------------------------------------------
# Async download internals
# ---------------------------------------------------------------------------


async def _download_http_file(
    client: httpx.AsyncClient,
    url: str,
    dest: Path,
    expected_sha256: str | None,
    label: str,
    status: JobStatus,
    progress_base: float,
    progress_span: float,
) -> None:
    """Download one file to dest with Range-resume and optional SHA-256 check.

    Writes to a .partial temp file; atomically renames to dest on success.
    Raises ValueError with MODEL_HASH_MISMATCH on hash failure (partial deleted).
    """
    temp_path = dest.with_suffix(dest.suffix + ".partial")
    dest.parent.mkdir(parents=True, exist_ok=True)

    resume_from = temp_path.stat().st_size if temp_path.exists() else 0
    download_complete = False

    for _attempt in range(2):
        request_headers: dict[str, str] = {}
        if resume_from > 0:
            request_headers["Range"] = f"bytes={resume_from}-"

        async with client.stream("GET", url, headers=request_headers, follow_redirects=True) as response:
            if response.status_code == 416:
                # Range not satisfiable — delete partial and restart fresh
                temp_path.unlink(missing_ok=True)
                resume_from = 0
                continue

            if resume_from > 0 and response.status_code == 200:
                # Server ignored Range header — restart without resume
                temp_path.unlink(missing_ok=True)
                resume_from = 0

            response.raise_for_status()

            content_length = int(response.headers.get("content-length", 0))
            total_size = resume_from + content_length
            downloaded = resume_from

            write_mode = "ab" if resume_from > 0 else "wb"
            with open(temp_path, write_mode) as output_file:
                async for chunk in response.aiter_bytes(chunk_size=_CHUNK_SIZE):
                    output_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        file_progress = min(downloaded / total_size, 1.0)
                        overall = progress_base + file_progress * progress_span
                        job_queue.update(status, progress=overall, state=JobState.RUNNING)

        download_complete = True
        break

    if not download_complete:
        raise RuntimeError(f"Download failed for {label}: server did not respond correctly")

    # SHA-256 verification (blocking read — run in thread)
    if expected_sha256 is not None:
        computed = await asyncio.to_thread(_compute_sha256, temp_path)
        if computed != expected_sha256:
            temp_path.unlink(missing_ok=True)
            raise ValueError(
                f"MODEL_HASH_MISMATCH: {label} — "
                f"expected {expected_sha256[:8]}…, got {computed[:8]}…"
            )
        log.info("SHA-256 verified: %s", label)
    else:
        log.warning("No SHA-256 in manifest for %s — integrity check skipped", label)

    temp_path.rename(dest)
    log.info("Downloaded %s → %s", label, dest)


# ---------------------------------------------------------------------------
# Job entry point
# ---------------------------------------------------------------------------


async def run_download_job(status: JobStatus, manifest_id: str, models_dir: Path) -> None:
    """Download + verify + register one manifest model."""
    entry = get_manifest_entry(manifest_id)
    if entry is None:
        raise ValueError(f"MODEL_NOT_FOUND: manifest_id={manifest_id!r}")

    model_dir = models_dir / manifest_id
    model_dir.mkdir(parents=True, exist_ok=True)

    if entry.hf_repo:
        log.info("HuggingFace download: %s → %s", entry.hf_repo, model_dir)
        job_queue.update(status, progress=0.05, state=JobState.RUNNING)
        await asyncio.to_thread(_hf_snapshot_sync, entry.hf_repo, model_dir)
        job_queue.update(status, progress=0.95, state=JobState.RUNNING)
        registry_path = str(model_dir)

    elif entry.format == "onnx_bundle":
        if not entry.files:
            raise ValueError(f"MODEL_INCOMPLETE: {manifest_id} has no file entries")

        file_info = entry.files[0]
        zip_dest = models_dir / f"{manifest_id}_download.zip"

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            await _download_http_file(
                client=client,
                url=file_info["url"],
                dest=zip_dest,
                expected_sha256=file_info.get("sha256"),
                label=f"{manifest_id}/{file_info['filename']}",
                status=status,
                progress_base=0.0,
                progress_span=0.85,
            )

        job_queue.update(status, progress=0.90, state=JobState.RUNNING)
        await asyncio.to_thread(_extract_zip, zip_dest, model_dir)
        registry_path = str(model_dir)

    else:
        if not entry.files:
            raise ValueError(f"MODEL_INCOMPLETE: {manifest_id} has no file entries")

        total_files = len(entry.files)
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for file_index, file_info in enumerate(entry.files):
                progress_base = (file_index / total_files) * 0.90
                progress_span = 0.90 / total_files
                dest = model_dir / file_info["filename"]

                await _download_http_file(
                    client=client,
                    url=file_info["url"],
                    dest=dest,
                    expected_sha256=file_info.get("sha256"),
                    label=f"{manifest_id}/{file_info['filename']}",
                    status=status,
                    progress_base=progress_base,
                    progress_span=progress_span,
                )

        registry_path = str(model_dir)

    # Transactional: register only after all files are verified and renamed
    await asyncio.to_thread(_register_model_in_db, manifest_id, entry, registry_path)
    log.info("Model %s installed at %s", manifest_id, registry_path)


async def enqueue_download(manifest_id: str, models_dir: Path) -> JobStatus:
    """Enqueue a managed model download job and return its status."""
    entry = get_manifest_entry(manifest_id)
    label = entry.name if entry else manifest_id
    return await job_queue.enqueue(
        kind=JobKind.DOWNLOAD,
        label=f"Download: {label}",
        coro_factory=lambda job_status: run_download_job(job_status, manifest_id, models_dir),
    )
