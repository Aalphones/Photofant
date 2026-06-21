"""ComfyUI template introspection -- parses API-format JSON, identifies nodes and image inputs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any  # noqa: TC003

IMAGE_LOADER_CLASSES = frozenset({
    "LoadImage",
    "LoadImageMask",
    "LoadImageFromUrl",
    "LoadImage (mtb)",
    "Image Load",
})

MASK_LOADER_CLASSES = frozenset({
    "LoadImageMask",
})

SAVE_IMAGE_CLASSES = frozenset({
    "SaveImage",
    "SaveAnimatedWEBP",
    "SaveAnimatedPNG",
    "PreviewImage",
})


@dataclass
class NodeInfo:
    node_id: str
    class_type: str
    title: str
    inputs: dict[str, Any]


@dataclass
class InputSuggestion:
    key: str
    label: str
    node_title: str
    node_id: str
    field: str
    kind: str  # image | mask
    required: bool
    lockable: bool


@dataclass
class IntrospectionResult:
    nodes: list[NodeInfo] = field(default_factory=list)
    input_suggestions: list[InputSuggestion] = field(default_factory=list)
    has_save_image: bool = False
    is_api_format: bool = True
    errors: list[str] = field(default_factory=list)


def introspect_template(template: dict[str, Any]) -> IntrospectionResult:
    """Parse a ComfyUI API-format template and extract node info + input suggestions."""
    result = IntrospectionResult()

    if not isinstance(template, dict):
        result.is_api_format = False
        result.errors.append("Template ist kein JSON-Objekt")
        return result

    if "last_node_id" in template or "last_link_id" in template:
        result.is_api_format = False
        result.errors.append(
            "Das ist ein UI-Format-Workflow — bitte als API-Format exportieren "
            "(ComfyUI → Save (API Format))"
        )
        return result

    for node_id, node_data in template.items():
        if not isinstance(node_data, dict):
            continue
        class_type = node_data.get("class_type", "")
        if not class_type:
            continue

        meta = node_data.get("_meta", {})
        title = meta.get("title", "") if isinstance(meta, dict) else ""
        node_inputs = node_data.get("inputs", {})
        if not isinstance(node_inputs, dict):
            node_inputs = {}

        node_info = NodeInfo(
            node_id=str(node_id),
            class_type=class_type,
            title=title or f"{class_type} [{node_id}]",
            inputs=node_inputs,
        )
        result.nodes.append(node_info)

        if class_type in SAVE_IMAGE_CLASSES:
            result.has_save_image = True

        if class_type in IMAGE_LOADER_CLASSES:
            kind = "mask" if class_type in MASK_LOADER_CLASSES else "image"
            input_field = "image"
            if class_type == "LoadImageMask":
                input_field = "image"

            safe_title = title or class_type
            safe_key = _title_to_key(safe_title)

            suggestion = InputSuggestion(
                key=safe_key,
                label=safe_title,
                node_title=title or f"{class_type} [{node_id}]",
                node_id=str(node_id),
                field=input_field,
                kind=kind,
                required=True,
                lockable=False,
            )
            result.input_suggestions.append(suggestion)

    if not result.has_save_image:
        result.errors.append(
            "Kein SaveImage-Node gefunden — Ergebnisse landen nicht in output/"
        )

    if not result.nodes:
        result.errors.append("Keine Nodes im Template gefunden")

    return result


def load_and_introspect(template_path: Path) -> IntrospectionResult:
    """Load a template file from disk and introspect it."""
    if not template_path.exists():
        result = IntrospectionResult()
        result.errors.append(f"Template-Datei nicht gefunden: {template_path}")
        return result

    try:
        raw = template_path.read_text(encoding="utf-8")
        template = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        result = IntrospectionResult()
        result.errors.append(f"Template-Datei nicht lesbar: {exc}")
        return result

    return introspect_template(template)


def _title_to_key(title: str) -> str:
    """Convert a node title to a safe key: lowercase, underscores, ASCII-only."""
    key = title.lower().strip()
    key = key.replace(" ", "_").replace("-", "_")
    cleaned = "".join(char for char in key if char.isalnum() or char == "_")
    return cleaned or "input"
