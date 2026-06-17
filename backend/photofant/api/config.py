"""GET /api/config, PATCH /api/config — app-wide key/value configuration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from photofant.config import get_data_root_base
from photofant.db.session import get_session

log = logging.getLogger(__name__)

router = APIRouter(prefix="/config")

DbSession = Annotated[Session, Depends(get_session)]

_DEFAULT_MODELS_DIR_NAME = "models"


def _default_models_dir() -> str:
    return str(get_data_root_base() / ".photofant" / _DEFAULT_MODELS_DIR_NAME)


def _read_config(session: Session) -> dict[str, str | None]:
    rows = session.execute(text("SELECT key, value FROM app_config")).fetchall()
    stored: dict[str, str | None] = {row[0]: row[1] for row in rows}
    # Inject defaults for keys not yet written to DB.
    return {
        "data_root": stored.get("data_root"),
        "models_dir": stored.get("models_dir") or _default_models_dir(),
        **{key: value for key, value in stored.items() if key not in {"data_root", "models_dir"}},
    }


class ConfigResponse(BaseModel):
    data: dict[str, str | None]


class ConfigPatchRequest(BaseModel):
    data: dict[str, str | None]


@router.get("", response_model=ConfigResponse)
def get_config(session: DbSession) -> ConfigResponse:
    """Return all app_config entries with defaults filled in."""
    return ConfigResponse(data=_read_config(session))


@router.patch("", response_model=ConfigResponse)
def patch_config(body: ConfigPatchRequest, session: DbSession) -> ConfigResponse:
    """Update one or more config keys. Unknown keys are stored as-is."""
    for key, value in body.data.items():
        existing = session.execute(
            text("SELECT 1 FROM app_config WHERE key = :key"),
            {"key": key},
        ).fetchone()
        if existing:
            session.execute(
                text("UPDATE app_config SET value = :value WHERE key = :key"),
                {"key": key, "value": value},
            )
        else:
            session.execute(
                text("INSERT INTO app_config (key, value) VALUES (:key, :value)"),
                {"key": key, "value": value},
            )
        log.info("config: %s = %r", key, value)

    if "models_dir" in body.data:
        models_dir = body.data["models_dir"]
        if models_dir:
            Path(models_dir).mkdir(parents=True, exist_ok=True)
            log.info("models_dir set to %s — directory ensured", models_dir)

    return ConfigResponse(data=_read_config(session))
