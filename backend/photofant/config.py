from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_DATA_ROOT = Path(__file__).parent.parent.parent / "Data"
_DEFAULT_MODELS_DIR_NAME = "models"
_PERSON_SUBFOLDERS = ["photos", "favourites", "faces", "edits"]


def get_data_root_base() -> Path:
    """Base data directory from settings.json (or default), without consulting the DB.

    The SQLite DB and thumbnail cache anchor their .photofant/ folder here, so the
    whole data set sits under one backup-able directory. Reads from settings.json
    instead of the DB to avoid a circular dependency (DB location can't depend on
    a value stored inside that same DB).
    """
    from photofant.settings import load_settings

    settings = load_settings()
    raw = settings.get("data_root")
    return Path(raw) if raw else _DEFAULT_DATA_ROOT


def get_data_root() -> Path:
    """Return the configured data root and ensure folder structure exists."""
    from photofant.settings import load_settings

    settings = load_settings()
    raw = settings.get("data_root")
    root = Path(raw) if raw else _DEFAULT_DATA_ROOT
    _ensure_folder_structure(root)
    return root


def get_models_dir() -> Path:
    """Return the configured models_dir from settings.json, ensuring it exists."""
    from photofant.settings import load_settings

    settings = load_settings()
    raw = settings.get("models_dir")
    models_dir = Path(raw) if raw else get_data_root_base() / ".photofant" / _DEFAULT_MODELS_DIR_NAME
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def _ensure_folder_structure(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    unknown_dir = root / "_unknown"
    for subfolder in _PERSON_SUBFOLDERS:
        (unknown_dir / subfolder).mkdir(parents=True, exist_ok=True)
    (root / ".photofant").mkdir(parents=True, exist_ok=True)
