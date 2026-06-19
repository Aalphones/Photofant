from __future__ import annotations

import os
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from photofant.db.cache import get_cache_db_path
from photofant.db.engine import get_db_path
from photofant.db.session import get_session

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]

_ENV_FLAGS = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")


class InfoResponse(BaseModel):
    version: str
    python_version: str
    db_path: str
    db_size_bytes: int
    cache_db_path: str
    cache_db_size_bytes: int
    onnx_version: str
    last_migration: str | None
    gpu_name: str | None
    vram_gb: float | None
    cuda_version: str | None
    env_flags: dict[str, str]


def _app_version() -> str:
    try:
        return version("photofant-backend")
    except PackageNotFoundError:
        return "dev"


def _onnx_version() -> str:
    try:
        import onnxruntime as ort  # type: ignore[import-untyped]
        return str(ort.__version__)
    except Exception:
        return "n/a"


def _gpu_details() -> tuple[str | None, float | None, str | None]:
    """Returns (gpu_name, vram_gb, cuda_version) — all None if CUDA unavailable."""
    try:
        import onnxruntime as ort
        if "CUDAExecutionProvider" not in ort.get_available_providers():
            return None, None, None
    except Exception:
        return None, None, None

    gpu_name: str | None = None
    vram_gb: float | None = None
    cuda_version: str | None = None

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("\n")[0].split(",")
            gpu_name = parts[0].strip() if len(parts) > 0 else None
            vram_mib_raw = parts[1].strip() if len(parts) > 1 else None
            if vram_mib_raw is not None:
                vram_gb = round(float(vram_mib_raw) / 1024, 1)
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, timeout=5, check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                match = re.search(r"CUDA Version:\s*([\d.]+)", line)
                if match:
                    cuda_version = match.group(1)
                    break
    except Exception:
        pass

    return gpu_name, vram_gb, cuda_version


@router.get("/info", response_model=InfoResponse)
async def get_info(session: DbSession) -> InfoResponse:
    db_path = get_db_path()
    cache_db_path = get_cache_db_path()

    db_size = db_path.stat().st_size if db_path.exists() else 0
    cache_db_size = cache_db_path.stat().st_size if cache_db_path.exists() else 0

    row = session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).one_or_none()
    last_migration = str(row[0]) if row else None

    gpu_name, vram_gb, cuda_version = _gpu_details()

    env_flags = {flag: os.environ[flag] for flag in _ENV_FLAGS if flag in os.environ}

    return InfoResponse(
        version=_app_version(),
        python_version=sys.version,
        db_path=str(db_path),
        db_size_bytes=db_size,
        cache_db_path=str(cache_db_path),
        cache_db_size_bytes=cache_db_size,
        onnx_version=_onnx_version(),
        last_migration=last_migration,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        cuda_version=cuda_version,
        env_flags=env_flags,
    )
