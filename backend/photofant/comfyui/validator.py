"""ComfyUI workflow validator -- checks bindings against the actual template."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from photofant.comfyui.introspect import IntrospectionResult


@dataclass
class ValidationError:
    code: str
    message: str
    expected: str
    found: str
    next_step: str


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)

    def add_error(
        self,
        code: str,
        message: str,
        expected: str = "",
        found: str = "",
        next_step: str = "",
    ) -> None:
        self.errors.append(ValidationError(
            code=code,
            message=message,
            expected=expected,
            found=found,
            next_step=next_step,
        ))
        self.is_valid = False

    def to_dicts(self) -> list[dict[str, str]]:
        return [
            {
                "code": error.code,
                "message": error.message,
                "expected": error.expected,
                "found": error.found,
                "next_step": error.next_step,
            }
            for error in self.errors
        ]


def validate_workflow(
    template: dict[str, Any],
    inputs: list[dict[str, Any]],
    params: list[dict[str, Any]],
) -> ValidationResult:
    """Validate input/param bindings against a parsed API-format template."""
    result = ValidationResult()

    title_to_nodes: dict[str, list[str]] = {}
    node_id_to_data: dict[str, dict[str, Any]] = {}
    has_save_image = False

    save_classes = {"SaveImage", "SaveAnimatedWEBP", "SaveAnimatedPNG", "PreviewImage"}

    for node_id, node_data in template.items():
        if not isinstance(node_data, dict):
            continue
        class_type = node_data.get("class_type", "")
        if not class_type:
            continue
        node_id_to_data[str(node_id)] = node_data

        meta = node_data.get("_meta", {})
        title = meta.get("title", "") if isinstance(meta, dict) else ""
        if title:
            title_to_nodes.setdefault(title, []).append(str(node_id))

        if class_type in save_classes:
            has_save_image = True

    if not has_save_image:
        result.add_error(
            code="no_save_image",
            message="Kein SaveImage-Node im Template",
            expected="Mindestens ein SaveImage-Node",
            found="Keiner gefunden",
            next_step="Einen SaveImage-Node zum Workflow hinzufuegen",
        )

    duplicate_titles = {
        title: ids for title, ids in title_to_nodes.items() if len(ids) > 1
    }

    for binding in inputs:
        _validate_binding(binding, title_to_nodes, node_id_to_data, duplicate_titles, result, "Input")

    for binding in params:
        _validate_binding(binding, title_to_nodes, node_id_to_data, duplicate_titles, result, "Param")

    return result


def _validate_binding(
    binding: dict[str, Any],
    title_to_nodes: dict[str, list[str]],
    node_id_to_data: dict[str, dict[str, Any]],
    duplicate_titles: dict[str, list[str]],
    result: ValidationResult,
    binding_type: str,
) -> None:
    """Validate a single input or param binding."""
    node_title = binding.get("node_title", "")
    node_id = binding.get("node_id", "")
    field_name = binding.get("field", "image")
    key = binding.get("key", "?")

    resolved_node_id: str | None = None

    if node_title:
        if node_title in duplicate_titles:
            node_ids = duplicate_titles[node_title]
            result.add_error(
                code="duplicate_title",
                message=f'{binding_type} "{key}": Titel "{node_title}" ist nicht eindeutig',
                expected=f'Titel "{node_title}" genau einmal im Template',
                found=f'{len(node_ids)} Nodes mit diesem Titel (IDs: {", ".join(node_ids)})',
                next_step="Im ComfyUI-Workflow dem Node einen eindeutigen Titel geben",
            )
            return

        if node_title not in title_to_nodes:
            result.add_error(
                code="title_not_found",
                message=f'{binding_type} "{key}": Titel "{node_title}" existiert nicht im Template',
                expected=f'Node mit Titel "{node_title}"',
                found="Kein passender Node",
                next_step="Titel im Workflow pruefen oder Binding anpassen",
            )
            return

        resolved_node_id = title_to_nodes[node_title][0]

    elif node_id:
        if str(node_id) not in node_id_to_data:
            result.add_error(
                code="node_id_not_found",
                message=f'{binding_type} "{key}": Node-ID "{node_id}" existiert nicht im Template',
                expected=f"Node mit ID {node_id}",
                found="Kein passender Node",
                next_step="Node-ID pruefen oder Binding anpassen",
            )
            return
        resolved_node_id = str(node_id)
    else:
        result.add_error(
            code="no_binding",
            message=f'{binding_type} "{key}": Weder node_title noch node_id angegeben',
            expected="node_title oder node_id",
            found="Beides leer",
            next_step="Einen Zielnode auswaehlen",
        )
        return

    if resolved_node_id and resolved_node_id in node_id_to_data:
        node_data = node_id_to_data[resolved_node_id]
        node_inputs = node_data.get("inputs", {})
        if isinstance(node_inputs, dict) and field_name not in node_inputs:
            available = ", ".join(sorted(node_inputs.keys())) if node_inputs else "(keine)"
            result.add_error(
                code="field_not_found",
                message=f'{binding_type} "{key}": Feld "{field_name}" existiert nicht im Zielnode',
                expected=f'Feld "{field_name}" im Node',
                found=f"Verfuegbare Felder: {available}",
                next_step="Feldnamen pruefen oder anderes Feld waehlen",
            )


def check_drift(
    template: dict[str, Any],
    inputs: list[dict[str, Any]],
    params: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Check for bindings that no longer match after a template re-import."""
    validation = validate_workflow(template, inputs, params)
    drift_entries: list[dict[str, str]] = []
    for error in validation.errors:
        if error.code in ("title_not_found", "node_id_not_found", "field_not_found", "duplicate_title"):
            drift_entries.append({
                "key": key_from_message(error.message),
                "type": error.code,
                "reason": error.message,
            })
    return drift_entries


def key_from_message(message: str) -> str:
    """Extract the key name from a validation error message."""
    start = message.find('"')
    if start == -1:
        return "?"
    end = message.find('"', start + 1)
    if end == -1:
        return "?"
    return message[start + 1:end]


def validate_introspection_result(
    template: dict[str, Any],
    introspection: IntrospectionResult,
) -> ValidationResult:
    """Validate that introspected prompt/resolution/mask nodes and fields exist in the template."""
    result = ValidationResult()

    node_id_to_data: dict[str, dict[str, Any]] = {
        str(node_id): node_data
        for node_id, node_data in template.items()
        if isinstance(node_data, dict)
    }

    def _check_field(label: str, node_id: str, field_name: str) -> None:
        if node_id not in node_id_to_data:
            result.add_error(
                code="introspect_node_missing",
                message=f'{label}: Node "{node_id}" existiert nicht im Template',
                expected=f"Node {node_id}",
                found="Nicht gefunden",
                next_step="Workflow erneut importieren",
            )
            return
        node_inputs = node_id_to_data[node_id].get("inputs", {})
        if isinstance(node_inputs, dict) and field_name not in node_inputs:
            available = ", ".join(sorted(node_inputs.keys())) if node_inputs else "(keine)"
            result.add_error(
                code="introspect_field_missing",
                message=f'{label}: Feld "{field_name}" fehlt in Node "{node_id}"',
                expected=f'Feld "{field_name}"',
                found=f"Verfügbare Felder: {available}",
                next_step="Workflow-Node prüfen",
            )

    if introspection.prompt is not None:
        _check_field("Prompt (positiv)", introspection.prompt.node_id, introspection.prompt.field)

    if introspection.negative_prompt is not None:
        _check_field(
            "Prompt (negativ)",
            introspection.negative_prompt.node_id,
            introspection.negative_prompt.field,
        )

    if introspection.resolution is not None:
        res = introspection.resolution
        _check_field("Resolution (megapixels)", res.node_id, res.megapixels_field)
        _check_field("Resolution (aspect_ratio)", res.node_id, res.aspect_field)

    if introspection.mask is not None and introspection.mask.mode == "alpha":
        mask_node_id = introspection.mask.image_node_id
        if mask_node_id not in node_id_to_data:
            result.add_error(
                code="introspect_mask_node_missing",
                message=f'Maske (Alpha): LoadImage-Node "{mask_node_id}" nicht gefunden',
                expected=f"LoadImage Node {mask_node_id}",
                found="Nicht gefunden",
                next_step="Workflow erneut importieren",
            )

    return result
