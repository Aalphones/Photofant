"""Filesystem-based ComfyUI workflow discovery — no DB, no activation gate."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from photofant.comfyui.introspect import IntrospectionResult, load_and_introspect


@dataclass
class WorkflowDiscoveryItem:
    key: str          # Dateiname ohne Endung (interner Name & Run-Selektor)
    name: str         # menschenlesbar (key, Underscores → Leerzeichen, Title Case)
    category: str     # upscale | img2img | inpaint | generic
    inputs: list[dict[str, str]]       # [{key, label, node_id, field, kind}]
    prompt: dict[str, str] | None      # {node_id, field}
    negative_prompt: dict[str, str] | None
    resolution: dict[str, Any] | None  # {node_id, megapixels_field, aspect_field, aspect_default}
    mask: dict[str, str] | None        # {mode, image_node_id}
    toggles: list[dict[str, Any]]      # [{key, label, node_id, field, default}]
    is_valid: bool
    errors: list[str]


def scan_workflows(workflows_dir: Path) -> list[WorkflowDiscoveryItem]:
    """Scan directory for *.json / *.api.json files, return discovery DTOs sorted by name.

    Deduplication: <key>.api.json takes priority over <key>.json for the same key.
    """
    if not workflows_dir.is_dir():
        return []

    # Collect files keyed by stem; .api.json beats .json
    files: dict[str, Path] = {}
    for path in workflows_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        stem = path.stem  # e.g. "flux_edit.api" or "flux_edit"
        key = stem[:-4] if stem.endswith(".api") else stem
        if key not in files or stem.endswith(".api"):
            files[key] = path

    items = [
        _to_discovery_item(key, load_and_introspect(path))
        for key, path in sorted(files.items())
    ]
    return sorted(items, key=lambda item: item.name.lower())


def load_workflow(workflows_dir: Path, key: str) -> WorkflowDiscoveryItem | None:
    """Load a single workflow by key (None if not found)."""
    path = _find_file(workflows_dir, key)
    if path is None:
        return None
    return _to_discovery_item(key, load_and_introspect(path))


def load_workflow_template(workflows_dir: Path, key: str) -> dict[str, Any] | None:
    """Load raw JSON template dict for a workflow key (None if not found/unreadable)."""
    path = _find_file(workflows_dir, key)
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_file(workflows_dir: Path, key: str) -> Path | None:
    for suffix in [f"{key}.api.json", f"{key}.json"]:
        candidate = workflows_dir / suffix
        if candidate.is_file():
            return candidate
    return None


def _to_discovery_item(key: str, introspection: IntrospectionResult) -> WorkflowDiscoveryItem:
    name = key.replace("_", " ").title()

    inputs = [
        {
            "key": suggestion.key,
            "label": suggestion.label,
            "node_id": suggestion.node_id,
            "field": suggestion.field,
            "kind": suggestion.kind,
        }
        for suggestion in introspection.input_suggestions
    ]

    prompt = (
        {"node_id": introspection.prompt.node_id, "field": introspection.prompt.field}
        if introspection.prompt else None
    )
    negative_prompt = (
        {"node_id": introspection.negative_prompt.node_id, "field": introspection.negative_prompt.field}
        if introspection.negative_prompt else None
    )
    resolution: dict[str, Any] | None = (
        {
            "node_id": introspection.resolution.node_id,
            "megapixels_field": introspection.resolution.megapixels_field,
            "aspect_field": introspection.resolution.aspect_field,
            "aspect_default": introspection.resolution.aspect_default,
        }
        if introspection.resolution else None
    )
    mask: dict[str, str] | None = (
        {"mode": introspection.mask.mode, "image_node_id": introspection.mask.image_node_id}
        if introspection.mask else None
    )

    toggles = [
        {
            "key": toggle.key,
            "label": toggle.label,
            "node_id": toggle.node_id,
            "field": toggle.field,
            "default": toggle.default,
        }
        for toggle in introspection.toggles
    ]

    is_valid = introspection.is_api_format and not introspection.errors

    return WorkflowDiscoveryItem(
        key=key,
        name=name,
        category=introspection.category,
        inputs=inputs,
        prompt=prompt,
        negative_prompt=negative_prompt,
        resolution=resolution,
        mask=mask,
        toggles=toggles,
        is_valid=is_valid,
        errors=introspection.errors,
    )
