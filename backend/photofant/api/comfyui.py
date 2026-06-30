"""
GET  /api/settings/comfyui              -- read ComfyUI settings block
PUT  /api/settings/comfyui              -- replace ComfyUI settings block
POST /api/comfyui/test-connection       -- probe ComfyUI /system_stats
GET  /api/comfyui/workflows             -- list all workflows (filesystem scan)
GET  /api/comfyui/workflows/{key}       -- get single workflow by key
POST /api/comfyui/workflows/introspect  -- introspect uploaded template JSON
POST /api/comfyui/workflows/{key}/run   -- fire-and-forget trigger (key-based)
GET  /api/comfyui/results               -- list output images (history + output_dir)
GET  /api/comfyui/results/view          -- proxy ComfyUI /view (CORS-free preview)
POST /api/comfyui/results/import        -- import a ComfyUI output as Edit-Version
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response as _FastAPIResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.comfyui.client import ComfyUIClient, ComfyUIError
from photofant.comfyui.discovery import load_workflow, load_workflow_template, scan_workflows
from photofant.comfyui.importer import ComfyUIOutputRef, import_comfyui_output, select_default_output_node_id
from photofant.comfyui.introspect import introspect_template
from photofant.config import get_data_root_base
from photofant.db.session import get_session
from photofant.settings import load_settings, save_settings

log = logging.getLogger(__name__)

settings_router = APIRouter(prefix="/settings/comfyui")
comfyui_router = APIRouter(prefix="/comfyui")

DbSession = Annotated[Session, Depends(get_session)]


def _workflows_dir() -> Path:
    base = get_data_root_base() / ".photofant" / "workflows"
    base.mkdir(parents=True, exist_ok=True)
    return base


# ── Schemas — Settings ────────────────────────────────────────────────────────

class ComfyUISettingsResponse(BaseModel):
    enabled: bool
    base_url: str
    client_id: str
    output_dir: str
    timeout: int
    default_upscale: str
    default_edit: str
    default_inpaint: str


class ComfyUISettingsPutRequest(BaseModel):
    enabled: bool
    base_url: str
    client_id: str
    output_dir: str
    timeout: int
    default_upscale: str = ""
    default_edit: str = ""
    default_inpaint: str = ""


# ── Schemas — Test-Connection ─────────────────────────────────────────────────

class TestConnectionResponse(BaseModel):
    ok: bool
    detail: str


# ── Schemas — Workflow Discovery ──────────────────────────────────────────────

class WorkflowInputDto(BaseModel):
    key: str
    label: str
    node_id: str
    field: str
    kind: str  # image | mask


class WorkflowDiscoveryDto(BaseModel):
    key: str
    name: str
    category: str
    inputs: list[WorkflowInputDto]
    prompt: dict[str, str] | None
    negative_prompt: dict[str, str] | None
    resolution: dict[str, Any] | None
    mask: dict[str, str] | None
    is_valid: bool
    errors: list[str]


# ── Schemas — Introspection (upload-based, for preview) ──────────────────────

class NodeInfoDto(BaseModel):
    node_id: str
    class_type: str
    title: str
    inputs: dict[str, Any]


class InputSuggestionDto(BaseModel):
    key: str
    label: str
    node_title: str
    node_id: str
    field: str
    kind: str
    required: bool
    lockable: bool


class IntrospectionResponse(BaseModel):
    nodes: list[NodeInfoDto]
    input_suggestions: list[InputSuggestionDto]
    has_save_image: bool
    is_api_format: bool
    errors: list[str]


# ── Schemas — Run ─────────────────────────────────────────────────────────────

class MaskRunRequest(BaseModel):
    asset_id: int
    mask_data_url: str


class ResolutionRunRequest(BaseModel):
    megapixels: float
    aspect_ratio: str


class RunRequest(BaseModel):
    inputs: dict[str, int | list[int]]
    face_inputs: dict[str, int | list[int]] = {}
    prompt: str | None = None
    negative_prompt: str | None = None
    resolution: ResolutionRunRequest | None = None
    mask: MaskRunRequest | None = None


class DefaultRunRequest(RunRequest):
    target_asset_ids: list[int]


class RunJobDto(BaseModel):
    job_id: str


class RunResponse(BaseModel):
    jobs: list[RunJobDto]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _discovery_to_dto(item: Any) -> WorkflowDiscoveryDto:
    return WorkflowDiscoveryDto(
        key=item.key,
        name=item.name,
        category=item.category,
        inputs=[WorkflowInputDto(**inp) for inp in item.inputs],
        prompt=item.prompt,
        negative_prompt=item.negative_prompt,
        resolution=item.resolution,
        mask=item.mask,
        is_valid=item.is_valid,
        errors=item.errors,
    )


def _get_comfyui_client() -> tuple[ComfyUIClient, dict[str, Any]]:
    """Load settings and return (client, comfyui_cfg). Raises 422 if disabled."""
    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    if not comfyui_cfg.get("enabled", False):
        raise HTTPException(
            status_code=422,
            detail="ComfyUI-Integration ist deaktiviert — zuerst in den Einstellungen aktivieren",
        )
    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui_cfg.get("timeout", 10))
    return ComfyUIClient(base_url=base_url, timeout=timeout), comfyui_cfg


def _check_connection(client: ComfyUIClient) -> None:
    """Probe ComfyUI; raises HTTP 503 if unreachable."""
    try:
        client.system_stats()
    except ComfyUIError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"ComfyUI nicht erreichbar: {exc.what_found}. {exc.next_step}.",
        ) from exc


# ── Settings routes ───────────────────────────────────────────────────────────

@settings_router.get("", response_model=ComfyUISettingsResponse)
def get_comfyui_settings() -> ComfyUISettingsResponse:
    cfg = load_settings()
    comfyui = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    return ComfyUISettingsResponse(
        enabled=bool(comfyui.get("enabled", False)),
        base_url=str(comfyui.get("base_url", "http://127.0.0.1:8188")),
        client_id=str(comfyui.get("client_id", "photofant")),
        output_dir=str(comfyui.get("output_dir", "")),
        timeout=int(comfyui.get("timeout", 10)),
        default_upscale=str(comfyui.get("default_upscale", "")),
        default_edit=str(comfyui.get("default_edit", "")),
        default_inpaint=str(comfyui.get("default_inpaint", "")),
    )


@settings_router.put("", response_model=ComfyUISettingsResponse)
def put_comfyui_settings(body: ComfyUISettingsPutRequest) -> ComfyUISettingsResponse:
    if body.timeout < 1 or body.timeout > 300:
        raise HTTPException(status_code=422, detail="timeout muss zwischen 1 und 300 Sekunden liegen")

    # Validate default keys: must either be empty or exist in the workflow directory
    workflows_dir = _workflows_dir()
    for field_name, key_value in [
        ("default_upscale", body.default_upscale),
        ("default_edit", body.default_edit),
        ("default_inpaint", body.default_inpaint),
    ]:
        if key_value and load_workflow(workflows_dir, key_value) is None:
            log.warning(
                "Default-Workflow-Key '%s' für %s nicht gefunden — wird als leer gespeichert",
                key_value,
                field_name,
            )

    cfg = load_settings()
    cfg["comfyui"] = {  # type: ignore[typeddict-item]
        "enabled": body.enabled,
        "base_url": body.base_url.strip(),
        "client_id": body.client_id.strip() or "photofant",
        "output_dir": body.output_dir.strip(),
        "timeout": body.timeout,
        "default_upscale": body.default_upscale.strip(),
        "default_edit": body.default_edit.strip(),
        "default_inpaint": body.default_inpaint.strip(),
    }
    save_settings(cfg)
    log.info("comfyui settings updated: enabled=%s url=%s", body.enabled, body.base_url)
    return get_comfyui_settings()


# ── Test-connection route ─────────────────────────────────────────────────────

@comfyui_router.post("/test-connection", response_model=TestConnectionResponse)
def test_connection() -> TestConnectionResponse:
    cfg = load_settings()
    comfyui = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    base_url = str(comfyui.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui.get("timeout", 10))

    client = ComfyUIClient(base_url=base_url, timeout=timeout)
    try:
        stats = client.system_stats()
        version = str(stats.get("system", {}).get("comfyui_version", "unbekannt"))  # type: ignore[union-attr]
        return TestConnectionResponse(ok=True, detail=f"ComfyUI {version} erreichbar")
    except ComfyUIError as exc:
        detail = f"{exc.what_expected} -- {exc.what_found}. {exc.next_step}."
        return TestConnectionResponse(ok=False, detail=detail)


# ── Workflow Discovery routes ─────────────────────────────────────────────────

@comfyui_router.get("/workflows", response_model=list[WorkflowDiscoveryDto])
def list_workflows() -> list[WorkflowDiscoveryDto]:
    items = scan_workflows(_workflows_dir())
    return [_discovery_to_dto(item) for item in items]


@comfyui_router.get("/workflows/{key}", response_model=WorkflowDiscoveryDto)
def get_workflow(key: str) -> WorkflowDiscoveryDto:
    item = load_workflow(_workflows_dir(), key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{key}' nicht gefunden")
    return _discovery_to_dto(item)


# ── Introspection (upload-based preview) ─────────────────────────────────────

@comfyui_router.post("/workflows/introspect", response_model=IntrospectionResponse)
async def introspect_workflow(template: UploadFile) -> IntrospectionResponse:
    content = await template.read()
    try:
        template_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Template ist kein valides JSON: {exc}") from exc

    result = introspect_template(template_data)

    return IntrospectionResponse(
        nodes=[
            NodeInfoDto(
                node_id=node.node_id,
                class_type=node.class_type,
                title=node.title,
                inputs=node.inputs,
            )
            for node in result.nodes
        ],
        input_suggestions=[
            InputSuggestionDto(
                key=suggestion.key,
                label=suggestion.label,
                node_title=suggestion.node_title,
                node_id=suggestion.node_id,
                field=suggestion.field,
                kind=suggestion.kind,
                required=suggestion.required,
                lockable=suggestion.lockable,
            )
            for suggestion in result.input_suggestions
        ],
        has_save_image=result.has_save_image,
        is_api_format=result.is_api_format,
        errors=result.errors,
    )


# ── Run (Fire-and-Forget, key-based) ─────────────────────────────────────────

@comfyui_router.post("/workflows/{key}/run", response_model=RunResponse)
async def run_workflow(key: str, body: RunRequest) -> RunResponse:
    from photofant.jobs.comfyui_run_job import enqueue_comfyui_runs, expand_batch

    # 1. Load workflow
    workflows_dir = _workflows_dir()
    workflow_item = load_workflow(workflows_dir, key)
    if workflow_item is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{key}' nicht gefunden")

    if not workflow_item.is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Workflow '{key}' ist nicht valide: {'; '.join(workflow_item.errors)}",
        )

    # 2. Check ComfyUI enabled + connection
    client, comfyui_cfg = _get_comfyui_client()
    _check_connection(client)

    # 3. Load raw template for patch_template
    template = load_workflow_template(workflows_dir, key)
    if template is None:
        raise HTTPException(status_code=500, detail=f"Template für '{key}' konnte nicht geladen werden")

    # 4. Build input_bindings from introspection (node_title needed for patch lookup)
    from photofant.comfyui.introspect import load_and_introspect
    workflow_path = None
    for suffix in [f"{key}.api.json", f"{key}.json"]:
        candidate = workflows_dir / suffix
        if candidate.is_file():
            workflow_path = candidate
            break
    if workflow_path is None:
        raise HTTPException(status_code=404, detail=f"Workflow-Datei für '{key}' nicht gefunden")

    introspection = load_and_introspect(workflow_path)
    input_bindings: list[dict[str, Any]] = [
        {
            "key": suggestion.key,
            "label": suggestion.label,
            "node_title": suggestion.node_title,
            "node_id": suggestion.node_id,
            "field": suggestion.field,
            "kind": suggestion.kind,
            "required": suggestion.required,
            "lockable": suggestion.lockable,
        }
        for suggestion in introspection.input_suggestions
    ]

    # 5. Validate required inputs
    required_keys = {b["key"] for b in input_bindings if b.get("required", True)}
    all_provided = set(body.inputs.keys()) | set(body.face_inputs.keys())
    # If mask is provided, its asset_id satisfies the image_node_id slot
    if body.mask and introspection.mask:
        mask_suggestion = next(
            (s for s in introspection.input_suggestions if s.node_id == introspection.mask.image_node_id),
            None,
        )
        if mask_suggestion:
            all_provided.add(mask_suggestion.key)
    missing = required_keys - all_provided
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Pflicht-Inputs fehlen: {', '.join(sorted(missing))}",
        )

    # 6. Handle mask: inject asset_id into inputs and determine mask_input_key
    resolved_inputs = dict(body.inputs)
    mask_input_key: str | None = None
    mask_data_url: str | None = None

    if body.mask and introspection.mask and introspection.mask.mode == "alpha":
        mask_suggestion = next(
            (s for s in introspection.input_suggestions if s.node_id == introspection.mask.image_node_id),
            None,
        )
        if mask_suggestion:
            mask_input_key = mask_suggestion.key
            mask_data_url = body.mask.mask_data_url
            resolved_inputs[mask_input_key] = body.mask.asset_id

    # 7. Build param_bindings for prompt / negative_prompt / resolution
    param_bindings: list[dict[str, Any]] = []
    param_values: dict[str, Any] = {}

    if body.prompt and introspection.prompt:
        param_bindings.append({
            "key": "_prompt",
            "node_title": "",
            "node_id": introspection.prompt.node_id,
            "field": introspection.prompt.field,
        })
        param_values["_prompt"] = body.prompt

    if body.negative_prompt and introspection.negative_prompt:
        param_bindings.append({
            "key": "_negative_prompt",
            "node_title": "",
            "node_id": introspection.negative_prompt.node_id,
            "field": introspection.negative_prompt.field,
        })
        param_values["_negative_prompt"] = body.negative_prompt

    if body.resolution and introspection.resolution:
        res = introspection.resolution
        param_bindings.append({
            "key": "_resolution_mp",
            "node_title": "",
            "node_id": res.node_id,
            "field": res.megapixels_field,
        })
        param_values["_resolution_mp"] = body.resolution.megapixels
        param_bindings.append({
            "key": "_resolution_ar",
            "node_title": "",
            "node_id": res.node_id,
            "field": res.aspect_field,
        })
        param_values["_resolution_ar"] = body.resolution.aspect_ratio

    # 8. Expand batch
    try:
        expanded = expand_batch(resolved_inputs, input_bindings, body.face_inputs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 9. Enqueue
    statuses = await enqueue_comfyui_runs(
        workflow_template=template,
        input_bindings=input_bindings,
        param_bindings=param_bindings,
        expanded_inputs=expanded,
        params=param_values,
        workflow_name=workflow_item.name,
        mask_input_key=mask_input_key,
        mask_data_url=mask_data_url,
    )

    return RunResponse(jobs=[RunJobDto(job_id=status.id) for status in statuses])


@comfyui_router.post("/defaults/{task}/run", response_model=RunResponse)
async def run_default_workflow(task: str, body: DefaultRunRequest) -> RunResponse:
    from photofant.jobs.comfyui_run_job import enqueue_comfyui_runs, expand_batch

    default_fields = {
        "upscale": "default_upscale",
        "edit": "default_edit",
        "inpaint": "default_inpaint",
    }
    default_field = default_fields.get(task)
    if default_field is None:
        raise HTTPException(status_code=404, detail=f"Default-Task '{task}' nicht bekannt")

    client, comfyui_cfg = _get_comfyui_client()
    _check_connection(client)

    key = str(comfyui_cfg.get(default_field, "")).strip()
    if not key:
        raise HTTPException(status_code=422, detail=f"Kein Default-Workflow fuer '{task}' gesetzt")

    workflows_dir = _workflows_dir()
    workflow_item = load_workflow(workflows_dir, key)
    if workflow_item is None:
        raise HTTPException(status_code=404, detail=f"Default-Workflow '{key}' nicht gefunden")

    if not workflow_item.is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Workflow '{key}' ist nicht valide: {'; '.join(workflow_item.errors)}",
        )

    template = load_workflow_template(workflows_dir, key)
    if template is None:
        raise HTTPException(status_code=500, detail=f"Template fuer '{key}' konnte nicht geladen werden")

    try:
        output_node_id = select_default_output_node_id(template)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    from photofant.comfyui.introspect import load_and_introspect

    workflow_path = None
    for suffix in [f"{key}.api.json", f"{key}.json"]:
        candidate = workflows_dir / suffix
        if candidate.is_file():
            workflow_path = candidate
            break
    if workflow_path is None:
        raise HTTPException(status_code=404, detail=f"Workflow-Datei fuer '{key}' nicht gefunden")

    introspection = load_and_introspect(workflow_path)
    input_bindings: list[dict[str, Any]] = [
        {
            "key": suggestion.key,
            "label": suggestion.label,
            "node_title": suggestion.node_title,
            "node_id": suggestion.node_id,
            "field": suggestion.field,
            "kind": suggestion.kind,
            "required": suggestion.required,
            "lockable": suggestion.lockable,
        }
        for suggestion in introspection.input_suggestions
    ]

    required_keys = {binding["key"] for binding in input_bindings if binding.get("required", True)}
    all_provided = set(body.inputs.keys()) | set(body.face_inputs.keys())
    if body.mask and introspection.mask:
        mask_suggestion = next(
            (
                suggestion
                for suggestion in introspection.input_suggestions
                if suggestion.node_id == introspection.mask.image_node_id
            ),
            None,
        )
        if mask_suggestion:
            all_provided.add(mask_suggestion.key)
    missing = required_keys - all_provided
    if missing:
        raise HTTPException(status_code=422, detail=f"Pflicht-Inputs fehlen: {', '.join(sorted(missing))}")

    resolved_inputs = dict(body.inputs)
    mask_input_key: str | None = None
    mask_data_url: str | None = None

    if body.mask and introspection.mask and introspection.mask.mode == "alpha":
        mask_suggestion = next(
            (
                suggestion
                for suggestion in introspection.input_suggestions
                if suggestion.node_id == introspection.mask.image_node_id
            ),
            None,
        )
        if mask_suggestion:
            mask_input_key = mask_suggestion.key
            mask_data_url = body.mask.mask_data_url
            resolved_inputs[mask_input_key] = body.mask.asset_id

    param_bindings: list[dict[str, Any]] = []
    param_values: dict[str, Any] = {}

    if body.prompt and introspection.prompt:
        param_bindings.append({
            "key": "_prompt",
            "node_title": "",
            "node_id": introspection.prompt.node_id,
            "field": introspection.prompt.field,
        })
        param_values["_prompt"] = body.prompt

    if body.negative_prompt and introspection.negative_prompt:
        param_bindings.append({
            "key": "_negative_prompt",
            "node_title": "",
            "node_id": introspection.negative_prompt.node_id,
            "field": introspection.negative_prompt.field,
        })
        param_values["_negative_prompt"] = body.negative_prompt

    if body.resolution and introspection.resolution:
        resolution = introspection.resolution
        param_bindings.append({
            "key": "_resolution_mp",
            "node_title": "",
            "node_id": resolution.node_id,
            "field": resolution.megapixels_field,
        })
        param_values["_resolution_mp"] = body.resolution.megapixels
        param_bindings.append({
            "key": "_resolution_ar",
            "node_title": "",
            "node_id": resolution.node_id,
            "field": resolution.aspect_field,
        })
        param_values["_resolution_ar"] = body.resolution.aspect_ratio

    try:
        expanded = expand_batch(resolved_inputs, input_bindings, body.face_inputs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if len(body.target_asset_ids) != len(expanded):
        raise HTTPException(
            status_code=422,
            detail=(
                "target_asset_ids muss genau zur Anzahl expandierter Jobs passen "
                f"(erwartet {len(expanded)}, erhalten {len(body.target_asset_ids)})"
            ),
        )

    statuses = await enqueue_comfyui_runs(
        workflow_template=template,
        input_bindings=input_bindings,
        param_bindings=param_bindings,
        expanded_inputs=expanded,
        params=param_values,
        workflow_name=workflow_item.name,
        mask_input_key=mask_input_key,
        mask_data_url=mask_data_url,
        auto_import_targets=body.target_asset_ids,
        auto_import_task=task,
        auto_import_workflow_key=key,
        auto_import_output_node_id=output_node_id,
    )

    return RunResponse(jobs=[RunJobDto(job_id=status.id) for status in statuses])


# ── Results ───────────────────────────────────────────────────────────────────

_IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".webp"})


class ComfyUIResultItem(BaseModel):
    filename: str
    subfolder: str
    source: str  # "history" | "output_dir"
    preview_url: str


class ComfyUIResultsResponse(BaseModel):
    items: list[ComfyUIResultItem]


def _extract_history_items(history: dict[str, Any]) -> list[ComfyUIResultItem]:
    items: list[ComfyUIResultItem] = []
    for _prompt_id, entry in history.items():
        outputs = entry.get("outputs", {}) if isinstance(entry, dict) else {}
        for _node_id, node_out in outputs.items():
            for img in node_out.get("images", []):
                filename = img.get("filename", "")
                subfolder = img.get("subfolder", "")
                if not filename:
                    continue
                items.append(ComfyUIResultItem(
                    filename=filename,
                    subfolder=subfolder,
                    source="history",
                    preview_url=f"/api/comfyui/results/view?filename={filename}&subfolder={subfolder}",
                ))
    return items


def _scan_output_dir(output_dir: str) -> list[ComfyUIResultItem]:
    if not output_dir:
        return []
    base = Path(output_dir)
    if not base.is_dir():
        return []
    files = sorted(
        (child for child in base.iterdir() if child.is_file() and child.suffix.lower() in _IMAGE_EXTS),
        key=lambda child: child.stat().st_mtime,
        reverse=True,
    )
    return [
        ComfyUIResultItem(
            filename=child.name,
            subfolder="",
            source="output_dir",
            preview_url=f"/api/comfyui/results/view?filename={child.name}&subfolder=",
        )
        for child in files[:50]
    ]


@comfyui_router.get("/results", response_model=ComfyUIResultsResponse)
def list_results(prompt_id: str | None = None) -> ComfyUIResultsResponse:
    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]

    items: list[ComfyUIResultItem] = []

    if prompt_id:
        base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
        timeout = float(comfyui_cfg.get("timeout", 10))
        history_client = ComfyUIClient(base_url=base_url, timeout=timeout)
        history = history_client.get_history(prompt_id)
        items.extend(_extract_history_items(history))

    output_dir = str(comfyui_cfg.get("output_dir", ""))
    dir_items = _scan_output_dir(output_dir)
    history_filenames = {item.filename for item in items}
    items.extend(item for item in dir_items if item.filename not in history_filenames)

    return ComfyUIResultsResponse(items=items)


@comfyui_router.get("/results/view")
def view_result(filename: str, subfolder: str = "") -> _FastAPIResponse:
    """Proxy ComfyUI /view — CORS-free preview for the frontend."""
    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]

    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui_cfg.get("timeout", 10))
    view_client = ComfyUIClient(base_url=base_url, timeout=timeout)
    _MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

    try:
        data = view_client.view_image(filename, subfolder)
        ext = Path(filename).suffix.lower()
        return _FastAPIResponse(content=data, media_type=_MEDIA_TYPES.get(ext, "image/png"))
    except ComfyUIError:
        pass

    output_dir = str(comfyui_cfg.get("output_dir", ""))
    if output_dir:
        candidates = [
            Path(output_dir) / subfolder / filename if subfolder else Path(output_dir) / filename,
            Path(output_dir) / filename,
        ]
        for candidate in candidates:
            if candidate.is_file():
                media_type = _MEDIA_TYPES.get(candidate.suffix.lower(), "image/png")
                return _FastAPIResponse(content=candidate.read_bytes(), media_type=media_type)

    raise HTTPException(
        status_code=404,
        detail=f"Datei '{filename}' nicht gefunden (weder in ComfyUI noch in output_dir)",
    )


# ── Import (ComfyUI output → Edit-Version) ────────────────────────────────────

class ComfyUIImportRequest(BaseModel):
    asset_id: int
    filename: str
    subfolder: str = ""


class ComfyUIImportResponse(BaseModel):
    version_id: int
    type: str
    path: str
    is_current: bool
    params: dict[str, Any] | None  # type: ignore[type-arg]
    thumbnail_url: str


@comfyui_router.post("/results/import", response_model=ComfyUIImportResponse, status_code=201)
async def import_comfyui_result(body: ComfyUIImportRequest, db: DbSession) -> ComfyUIImportResponse:
    """Fetch a ComfyUI output image and import it as an Edit-Version (type=comfyui)."""
    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui_cfg.get("timeout", 10))
    output_dir = str(comfyui_cfg.get("output_dir", ""))

    import_client = ComfyUIClient(base_url=base_url, timeout=timeout)
    try:
        imported = import_comfyui_output(
            db,
            import_client,
            asset_id=body.asset_id,
            output=ComfyUIOutputRef(filename=body.filename, subfolder=body.subfolder),
            output_dir=output_dir,
            params={"source": "comfyui"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ComfyUIImportResponse(
        version_id=imported.version_id,
        type=imported.version_type,
        path=imported.path,
        is_current=imported.is_current,
        params=imported.params,
        thumbnail_url=imported.thumbnail_url,
    )
