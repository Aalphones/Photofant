from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

_DEFAULT_DATA_ROOT = Path("Data")
_PERSON_SUBFOLDERS = ["photos", "favourites", "faces", "edits"]


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


def _ensure_folder_structure(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    unknown_dir = root / "_unknown"
    for subfolder in _PERSON_SUBFOLDERS:
        (unknown_dir / subfolder).mkdir(parents=True, exist_ok=True)
    (root / ".photofant").mkdir(parents=True, exist_ok=True)
