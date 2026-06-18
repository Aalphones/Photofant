"""Manifest loader — loads and validates manifest.json at startup."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MANIFEST_PATH = Path(__file__).parent / "manifest.json"

_REQUIRED_FIELDS: frozenset[str] = frozenset({"id", "role", "name", "format", "tier"})
_VALID_ROLES: frozenset[str] = frozenset({"face", "tagger", "captioner", "semantic_search", "rembg"})

# Module-level cache — loaded once per process.
_manifest_cache: list[dict[str, Any]] | None = None


class ManifestEntry:
    """Typed wrapper around a raw manifest dict."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.id: str = raw["id"]
        self.role: str = raw["role"]
        self.name: str = raw["name"]
        self.variant: str | None = raw.get("variant")
        self.format: str = raw["format"]
        self.caption_mode: str | None = raw.get("caption_mode")
        self.capabilities: dict[str, Any] | None = raw.get("capabilities")
        self.hf_repo: str | None = raw.get("hf_repo")
        self.hf_allow_patterns: list[str] | None = raw.get("hf_allow_patterns") or None
        self.files: list[dict[str, Any]] = raw.get("files", [])
        self.size_bytes: int | None = raw.get("size_bytes")
        self.license_note: str | None = raw.get("license_note")
        self.requires_license_ack: bool = bool(raw.get("requires_license_ack", False))
        self.tier: str = raw["tier"]


def load_manifest() -> list[ManifestEntry]:
    """Return parsed + validated manifest entries; cached after first load."""
    global _manifest_cache
    if _manifest_cache is not None:
        return [ManifestEntry(raw) for raw in _manifest_cache]

    try:
        raw_text = MANIFEST_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.error("manifest.json not found at %s — model management will be unavailable", MANIFEST_PATH)
        _manifest_cache = []
        return []
    except OSError as error:
        log.error("Could not read manifest.json: %s", error)
        _manifest_cache = []
        return []

    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as error:
        log.error("manifest.json is invalid JSON: %s", error)
        _manifest_cache = []
        return []

    if data.get("schema_version") != 1:
        log.warning("Unexpected manifest schema_version: %s", data.get("schema_version"))

    raw_models: list[dict[str, Any]] = data.get("models", [])
    valid: list[dict[str, Any]] = []
    for entry in raw_models:
        missing = _REQUIRED_FIELDS - entry.keys()
        if missing:
            log.warning("Manifest entry %r missing required fields: %s — skipping", entry.get("id"), missing)
            continue
        if entry["role"] not in _VALID_ROLES:
            log.warning("Unknown role %r for manifest entry %r — skipping", entry["role"], entry["id"])
            continue
        valid.append(entry)

    log.info("Manifest loaded: %d valid model(s) from %s", len(valid), MANIFEST_PATH)
    _manifest_cache = valid
    return [ManifestEntry(raw) for raw in valid]


def get_manifest_entry(manifest_id: str) -> ManifestEntry | None:
    """Return a single manifest entry by id, or None if not found."""
    for entry in load_manifest():
        if entry.id == manifest_id:
            return entry
    return None
