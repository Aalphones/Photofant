"""Central settings module — reads/writes .photofant/settings.json."""
from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, TypedDict

log = logging.getLogger(__name__)


class DisplaySettings(TypedDict):
    locale: str
    date_format: str


class ComfyUISettings(TypedDict):
    enabled: bool
    base_url: str
    client_id: str
    output_dir: str
    timeout: int
    default_upscale: str   # Workflow-key für Upscale-Aufgabe (leer = keiner)
    default_edit: str      # Workflow-key für Image-Edit-Aufgabe
    default_inpaint: str   # Workflow-key für Inpaint-Aufgabe
    result_poll_interval_seconds: float
    result_wait_timeout_seconds: int


class AppSettings(TypedDict):
    _schema_version: int
    data_root: str | None
    db_path: str | None
    cache_db_path: str | None
    models_dir: str | None
    password: str | None
    auto_tag: bool
    auto_caption: bool
    auto_embed: bool
    auto_face: bool
    active_captioner: str
    min_probability: float
    max_tags: int
    tagging_threshold: float  # deprecated — kept for backward-compatible loading
    blur_threshold: float
    trash_auto_days: int
    keyboard_shortcuts: dict[str, Any] | None
    dupe_threshold: int  # deprecated — kept for backward-compatible loading, scan ignores it (ADR-007)
    dupe_phash_enabled: bool
    dupe_clip_enabled: bool
    dupe_clip_threshold: float
    face_det_conf_threshold: float
    face_det_iou_threshold: float
    face_crop_padding: int
    face_auto_threshold: float
    face_review_threshold: float
    face_min_cluster_size: int
    display: DisplaySettings
    comfyui: ComfyUISettings


SETTINGS_DEFAULTS: AppSettings = {
    "_schema_version": 1,
    "data_root": None,
    "db_path": None,
    "cache_db_path": None,
    "models_dir": None,
    "password": None,
    "auto_tag": True,
    "auto_caption": True,
    "auto_embed": True,
    "auto_face": True,
    "active_captioner": "florence-2-base",
    "min_probability": 0.5,
    "max_tags": 30,
    "tagging_threshold": 0.35,
    "blur_threshold": 200.0,
    "trash_auto_days": 30,
    "keyboard_shortcuts": None,
    "dupe_threshold": 10,
    "dupe_phash_enabled": True,
    "dupe_clip_enabled": True,
    "dupe_clip_threshold": 0.15,
    "face_det_conf_threshold": 0.5,
    "face_det_iou_threshold": 0.45,
    "face_crop_padding": 40,
    "face_auto_threshold": 0.6,
    "face_review_threshold": 0.45,
    "face_min_cluster_size": 3,
    "tagging_workers": 1,
    "captioning_workers": 1,
    "display": {
        "locale": "de",
        "date_format": "dmy",
    },
    "comfyui": {
        "enabled": False,
        "base_url": "http://127.0.0.1:8188",
        "client_id": "photofant",
        "output_dir": "",
        "timeout": 10,
        "default_upscale": "",
        "default_edit": "",
        "default_inpaint": "",
        "result_poll_interval_seconds": 1.0,
        "result_wait_timeout_seconds": 1800,
    },
}

# Maps known top-level keys to their expected Python types.
# bool must come before int in tuples (bool is a subclass of int).
_EXPECTED_TYPES: dict[str, type | tuple[type, ...]] = {
    "data_root": (str, type(None)),
    "db_path": (str, type(None)),
    "cache_db_path": (str, type(None)),
    "models_dir": (str, type(None)),
    "password": (str, type(None)),
    "auto_tag": bool,
    "auto_caption": bool,
    "auto_embed": bool,
    "auto_face": bool,
    "active_captioner": str,
    "min_probability": (float, int),
    "max_tags": int,
    "tagging_threshold": (float, int),
    "blur_threshold": (float, int),
    "trash_auto_days": int,
    "keyboard_shortcuts": (dict, type(None)),
    "dupe_threshold": int,
    "dupe_phash_enabled": bool,
    "dupe_clip_enabled": bool,
    "dupe_clip_threshold": (float, int),
    "face_det_conf_threshold": (float, int),
    "face_det_iou_threshold": (float, int),
    "face_crop_padding": int,
    "face_auto_threshold": (float, int),
    "face_review_threshold": (float, int),
    "face_min_cluster_size": int,
    "tagging_workers": int,
    "captioning_workers": int,
    "display": dict,
    "comfyui": dict,
}


def _default_settings_dir() -> Path:
    # Anchored to repo root — independent of CWD so backend/ can be the uvicorn working dir
    return Path(__file__).parent.parent.parent / "Data" / ".photofant"


def get_settings_path() -> Path:
    env_path = os.environ.get("PHOTOFANT_SETTINGS_PATH")
    if env_path:
        return Path(env_path)
    settings_dir = _default_settings_dir()
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "settings.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> AppSettings:
    path = get_settings_path()
    if not path.exists():
        return copy.deepcopy(SETTINGS_DEFAULTS)
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        merged = _deep_merge(dict(SETTINGS_DEFAULTS), raw)
        return merged  # type: ignore[return-value]
    except json.JSONDecodeError as error:
        log.warning("settings.json contains invalid JSON (%s) — falling back to defaults", error)
        return copy.deepcopy(SETTINGS_DEFAULTS)


def save_settings(settings: AppSettings) -> None:
    path = get_settings_path()
    tmp_path = path.parent / (path.name + ".tmp")
    tmp_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def patch_settings(partial: dict[str, Any]) -> AppSettings:
    for key, value in partial.items():
        if key not in _EXPECTED_TYPES:
            continue
        expected = _EXPECTED_TYPES[key]
        # For bool fields, reject bare int so True/False aren't accidentally overwritten with 1/0.
        if isinstance(expected, type) and expected is bool and not isinstance(value, bool):
            raise TypeError(f"Setting '{key}' expects bool, got {type(value).__name__}")
        if not isinstance(value, expected):
            raise TypeError(
                f"Setting '{key}' expects {expected}, got {type(value).__name__}"
            )
    current = load_settings()
    updated: AppSettings = _deep_merge(dict(current), partial)  # type: ignore[assignment]
    save_settings(updated)
    return updated


def ensure_settings_file() -> None:
    path = get_settings_path()
    if not path.exists():
        log.info("First start — creating default settings.json at %s", path)
        save_settings(copy.deepcopy(SETTINGS_DEFAULTS))
