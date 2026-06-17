from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

_DEFAULT_DATA_ROOT = Path("Data")
_PERSON_SUBFOLDERS = ["photos", "favourites", "faces", "edits"]


def get_data_root_base() -> Path:
    """Base data directory from env or default, *without* consulting the DB.

    Single source of truth for where everything lives. The SQLite DB and the
    thumbnail cache anchor their `.photofant/` folder here so the whole data set
    sits under one backup-able directory. This deliberately cannot read the
    DB-stored `data_root` override — the database file location can't depend on
    a value stored inside that same database.
    """
    env_root = os.environ.get("PHOTOFANT_DATA_ROOT")
    return Path(env_root) if env_root else _DEFAULT_DATA_ROOT


def get_data_root(session: Session | None = None) -> Path:
    """Return the configured data root and ensure folder structure exists."""
    env_root = os.environ.get("PHOTOFANT_DATA_ROOT")
    if env_root:
        root = Path(env_root)
    elif session is not None:
        from sqlalchemy import text

        row = session.execute(text("SELECT value FROM app_config WHERE key = 'data_root'")).fetchone()
        root = Path(row[0]) if (row and row[0]) else _DEFAULT_DATA_ROOT
    else:
        root = _DEFAULT_DATA_ROOT

    _ensure_folder_structure(root)
    return root


def get_models_dir(session: Session) -> Path:
    """Return the configured models_dir from DB config, ensuring it exists."""
    from sqlalchemy import text

    row = session.execute(text("SELECT value FROM app_config WHERE key = 'models_dir'")).fetchone()
    if row and row[0]:
        models_dir = Path(row[0])
    else:
        models_dir = get_data_root_base() / ".photofant" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def _ensure_folder_structure(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    unknown_dir = root / "_unknown"
    for subfolder in _PERSON_SUBFOLDERS:
        (unknown_dir / subfolder).mkdir(parents=True, exist_ok=True)
    (root / ".photofant").mkdir(parents=True, exist_ok=True)
