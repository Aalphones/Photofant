"""ComfyUI template introspection -- parses API-format JSON, identifies nodes and image inputs."""
from __future__ import annotations

import enum
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
    "ImageBatchLoader",
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

UPSCALE_NODE_CLASSES = frozenset({
    "SeedVR2VideoUpscaler",
    "UltimateSDUpscale",
    "ImageUpscaleWithModel",
    "UpscaleModelLoader",
})

INPAINT_NODE_CLASSES = frozenset({
    "InpaintModelConditioning",
})

IMG2IMG_NODE_CLASSES = frozenset({
    "ReferenceLatent",
})


class WorkflowCategory(enum.StrEnum):
    UPSCALE = "upscale"
    IMG2IMG = "img2img"
    INPAINT = "inpaint"
    GENERIC = "generic"


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
class PromptInfo:
    node_id: str
    field: str  # 'text' for CLIPTextEncode


@dataclass
class ResolutionInfo:
    node_id: str
    megapixels_field: str
    aspect_field: str
    aspect_default: str


@dataclass
class MaskInfo:
    mode: str  # 'alpha' | 'loader'
    image_node_id: str  # LoadImage node providing the alpha, or LoadImageMask node


@dataclass
class ToggleInfo:
    key: str
    label: str
    node_title: str
    node_id: str
    field: str
    default: bool


@dataclass
class IntrospectionResult:
    nodes: list[NodeInfo] = field(default_factory=list)
    input_suggestions: list[InputSuggestion] = field(default_factory=list)
    has_save_image: bool = False
    is_api_format: bool = True
    errors: list[str] = field(default_factory=list)
    prompt: PromptInfo | None = None
    negative_prompt: PromptInfo | None = None
    resolution: ResolutionInfo | None = None
    mask: MaskInfo | None = None
    toggles: list[ToggleInfo] = field(default_factory=list)
    category: str = WorkflowCategory.GENERIC


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
            elif class_type == "ImageBatchLoader":
                input_field = "image_paths"

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

    result.prompt, result.negative_prompt = _detect_prompts(result.nodes)
    result.resolution = _detect_resolution(result.nodes)
    result.mask = _detect_mask(result.nodes, template)
    result.toggles = _detect_toggles(result.nodes)
    result.category = _detect_category(result.nodes, result.mask)

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


def _detect_prompts(nodes: list[NodeInfo]) -> tuple[PromptInfo | None, PromptInfo | None]:
    """Detect positive and negative prompt nodes via title heuristic.

    Only matches CLIPTextEncode nodes whose title explicitly contains
    'positive' or 'negative' (case-insensitive). No single-encode fallback —
    internal upscaler prompts without explicit title markers are intentionally skipped.
    """
    positive: PromptInfo | None = None
    negative: PromptInfo | None = None
    for node in nodes:
        if node.class_type != "CLIPTextEncode":
            continue
        title_lower = node.title.lower()
        if "positive" in title_lower:
            positive = PromptInfo(node_id=node.node_id, field="text")
        elif "negative" in title_lower:
            negative = PromptInfo(node_id=node.node_id, field="text")
    return positive, negative


def _detect_resolution(nodes: list[NodeInfo]) -> ResolutionInfo | None:
    """Detect a ResolutionSelector node and extract its field names and default value."""
    for node in nodes:
        if node.class_type == "ResolutionSelector":
            aspect_default = node.inputs.get("aspect_ratio", "")
            return ResolutionInfo(
                node_id=node.node_id,
                megapixels_field="megapixels",
                aspect_field="aspect_ratio",
                aspect_default=str(aspect_default),
            )
    return None


def _detect_mask(nodes: list[NodeInfo], template: dict[str, Any]) -> MaskInfo | None:
    """Detect how a mask is provided in the workflow.

    Alpha-path: some node has input mask=[loadImageId, 1] where loadImageId is a LoadImage.
    Loader-path: a LoadImageMask node is present (existing behavior, kind=mask).
    """
    load_image_ids = {node.node_id for node in nodes if node.class_type == "LoadImage"}

    # Alpha-path: scan all nodes for mask: [X, 1] where X is a LoadImage
    for _node_id, node_data in template.items():
        if not isinstance(node_data, dict):
            continue
        node_inputs = node_data.get("inputs", {})
        if not isinstance(node_inputs, dict):
            continue
        mask_input = node_inputs.get("mask")
        if isinstance(mask_input, list) and len(mask_input) == 2:  # noqa: PLR2004
            source_node_id = str(mask_input[0])
            output_index = mask_input[1]
            if output_index == 1 and source_node_id in load_image_ids:
                return MaskInfo(mode="alpha", image_node_id=source_node_id)

    # Loader-path: LoadImageMask present
    for node in nodes:
        if node.class_type in MASK_LOADER_CLASSES:
            return MaskInfo(mode="loader", image_node_id=node.node_id)

    return None


def _detect_toggles(nodes: list[NodeInfo]) -> list[ToggleInfo]:
    """Detect on/off switch nodes and expose their literal boolean widget as a toggle.

    Heuristic: a node whose class_type contains "switch" (case-insensitive) — the common
    naming for ComfyUI nodes that route between two branches (e.g. on_true/on_false) based
    on a plain boolean widget. Only widget values (literal bool, not a link) qualify —
    links are two-element lists ([node_id, output_index]), never a bare bool.
    Label comes from the node's `_meta.title` so the run bar shows what the toggle
    actually does (e.g. "With NSFW Lora"), not the internal field name.
    """
    toggles: list[ToggleInfo] = []
    for node in nodes:
        if "switch" not in node.class_type.lower():
            continue
        safe_title = node.title if not node.title.startswith(node.class_type) else node.class_type
        used_keys = {toggle.key for toggle in toggles}
        for field_name, field_value in node.inputs.items():
            if not isinstance(field_value, bool):
                continue
            toggle_key = _title_to_key(safe_title)
            if toggle_key in used_keys:
                toggle_key = _title_to_key(f"{safe_title}_{field_name}")
            used_keys.add(toggle_key)
            toggles.append(
                ToggleInfo(
                    key=toggle_key,
                    label=safe_title,
                    node_title=node.title,
                    node_id=node.node_id,
                    field=field_name,
                    default=field_value,
                )
            )
    return toggles


def _detect_category(nodes: list[NodeInfo], mask: MaskInfo | None) -> str:
    """Heuristically assign a workflow category based on node class signatures."""
    class_types = {node.class_type for node in nodes}

    if class_types & UPSCALE_NODE_CLASSES:
        return WorkflowCategory.UPSCALE

    if mask is not None or class_types & INPAINT_NODE_CLASSES:
        return WorkflowCategory.INPAINT

    if class_types & IMG2IMG_NODE_CLASSES:
        return WorkflowCategory.IMG2IMG

    return WorkflowCategory.GENERIC
