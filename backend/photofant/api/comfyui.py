"""
GET  /api/settings/comfyui            -- read ComfyUI settings block
PUT  /api/settings/comfyui            -- replace ComfyUI settings block
POST /api/comfyui/test-connection      -- probe ComfyUI /system_stats
GET  /api/comfyui/workflows            -- list all workflows
POST /api/comfyui/workflows            -- create workflow (template upload)
GET  /api/comfyui/workflows/{id}       -- get single workflow
PATCH /api/comfyui/workflows/{id}      -- update workflow
DELETE /api/comfyui/workflows/{id}     -- delete workflow
POST /api/comfyui/workflows/introspect -- introspect template JSON
POST /api/comfyui/workflows/{id}/activate   -- activate (with validation gate)
POST /api/comfyui/workflows/{id}/deactivate -- deactivate
POST /api/comfyui/workflows/{id}/duplicate  -- duplicate workflow
POST /api/comfyui/workflows/{id}/revalidate -- re-validate after template change
POST /api/comfyui/workflows/{id}/run        -- fire-and-forget trigger (Phase 3)
GET  /api/comfyui/results              -- list output images (history + output_dir)
GET  /api/comfyui/results/view         -- proxy ComfyUI /view (CORS-free preview)
POST /api/comfyui/results/import       -- import a ComfyUI output as Edit-Version (Phase 5)
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid as _uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response as _FastAPIResponse
from PIL import Image as _Image
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.comfyui.client import ComfyUIClient, ComfyUIError
from photofant.comfyui.introspect import introspect_template
from photofant.comfyui.validator import validate_workflow
from photofant.config import get_data_root, get_data_root_base
from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
from photofant.db.models import AssetInstance, ComfyUIWorkflow, Person, Version
from photofant.db.session import get_session
from photofant.media.person_folders import ensure_person_folder
from photofant.media.thumbnails import generate_thumbnail
from photofant.settings import load_settings, save_settings

log = logging.getLogger(__name__)

settings_router = APIRouter(prefix="/settings/comfyui")
comfyui_router = APIRouter(prefix="/comfyui")

DbSession = Annotated[Session, Depends(get_session)]


def _workflows_dir() -> Path:
    base = get_data_root_base() / ".photofant" / "workflows"
    base.mkdir(parents=True, exist_ok=True)
    return base


# -- Schemas ------------------------------------------------------------------

class ComfyUISettingsResponse(BaseModel):
    enabled: bool
    base_url: str
    client_id: str
    output_dir: str
    timeout: int


class ComfyUISettingsPutRequest(BaseModel):
    enabled: bool
    base_url: str
    client_id: str
    output_dir: str
    timeout: int


class TestConnectionResponse(BaseModel):
    ok: bool
    detail: str


class WorkflowInputDto(BaseModel):
    key: str
    label: str
    node_title: str
    node_id: str = ""
    field: str = "image"
    kind: str = "image"
    required: bool = True
    lockable: bool = False


class WorkflowParamDto(BaseModel):
    key: str
    label: str
    node_title: str
    node_id: str = ""
    field: str
    type: str = "float"
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[str] | None = None


class WorkflowResponse(BaseModel):
    id: int
    name: str
    category: str
    template_path: str
    inputs: list[WorkflowInputDto]
    params: list[WorkflowParamDto]
    is_active: bool
    is_valid: bool
    validation_errors: list[dict[str, str]] | None
    created_at: str | None
    updated_at: str | None


class WorkflowCreateRequest(BaseModel):
    name: str
    category: str = "generic"
    inputs: list[WorkflowInputDto] = []
    params: list[WorkflowParamDto] = []


class WorkflowUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    inputs: list[WorkflowInputDto] | None = None
    params: list[WorkflowParamDto] | None = None


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


# -- Helpers ------------------------------------------------------------------

def _workflow_to_response(workflow: ComfyUIWorkflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        category=workflow.category,
        template_path=workflow.template_path,
        inputs=[WorkflowInputDto(**inp) for inp in (workflow.inputs or [])],
        params=[WorkflowParamDto(**param) for param in (workflow.params or [])],
        is_active=workflow.is_active,
        is_valid=workflow.is_valid,
        validation_errors=workflow.validation_errors,
        created_at=workflow.created_at.isoformat() if workflow.created_at else None,
        updated_at=workflow.updated_at.isoformat() if workflow.updated_at else None,
    )


def _load_template(template_path: str) -> dict[str, Any]:
    path = Path(template_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Template-Datei nicht gefunden: {template_path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"Template nicht lesbar: {exc}") from exc


def _run_validation(workflow: ComfyUIWorkflow) -> None:
    template = _load_template(workflow.template_path)
    inputs_dicts = workflow.inputs or []
    params_dicts = workflow.params or []
    result = validate_workflow(template, inputs_dicts, params_dicts)
    workflow.is_valid = result.is_valid
    workflow.validation_errors = result.to_dicts() if result.errors else None
    if not result.is_valid:
        workflow.is_active = False


# -- Settings routes ----------------------------------------------------------

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
    )


@settings_router.put("", response_model=ComfyUISettingsResponse)
def put_comfyui_settings(body: ComfyUISettingsPutRequest) -> ComfyUISettingsResponse:
    if body.timeout < 1 or body.timeout > 300:
        raise HTTPException(status_code=422, detail="timeout muss zwischen 1 und 300 Sekunden liegen")
    cfg = load_settings()
    cfg["comfyui"] = {  # type: ignore[typeddict-item]
        "enabled": body.enabled,
        "base_url": body.base_url.strip(),
        "client_id": body.client_id.strip() or "photofant",
        "output_dir": body.output_dir.strip(),
        "timeout": body.timeout,
    }
    save_settings(cfg)
    log.info("comfyui settings updated: enabled=%s url=%s", body.enabled, body.base_url)
    return ComfyUISettingsResponse(**cfg["comfyui"])  # type: ignore[typeddict-item]


# -- Test-connection route ----------------------------------------------------

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


# -- Workflow CRUD ------------------------------------------------------------

@comfyui_router.get("/workflows", response_model=list[WorkflowResponse])
def list_workflows(db: DbSession) -> list[WorkflowResponse]:
    workflows = db.query(ComfyUIWorkflow).order_by(ComfyUIWorkflow.name).all()
    return [_workflow_to_response(workflow) for workflow in workflows]


@comfyui_router.post("/workflows", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    db: DbSession,
    template: UploadFile,
    name: str = "Neuer Workflow",
    category: str = "generic",
) -> WorkflowResponse:
    if not template.filename or not template.filename.endswith(".json"):
        raise HTTPException(status_code=422, detail="Template muss eine .json-Datei sein")

    content = await template.read()
    try:
        template_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Template ist kein valides JSON: {exc}") from exc

    introspection = introspect_template(template_data)
    if not introspection.is_api_format:
        detail = introspection.errors[0] if introspection.errors else "Kein API-Format"
        raise HTTPException(status_code=422, detail=detail)

    dest_dir = _workflows_dir()
    safe_name = "".join(char for char in name.lower().replace(" ", "_") if char.isalnum() or char == "_") or "workflow"
    dest_path = dest_dir / f"{safe_name}.api.json"
    counter = 1
    while dest_path.exists():
        dest_path = dest_dir / f"{safe_name}_{counter}.api.json"
        counter += 1

    dest_path.write_bytes(content)

    auto_inputs = [
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

    now = datetime.now(UTC).replace(tzinfo=None)
    workflow = ComfyUIWorkflow(
        name=name,
        category=category,
        template_path=str(dest_path.resolve()),
        inputs=auto_inputs,
        params=[],
        is_active=False,
        is_valid=False,
        validation_errors=None,
        created_at=now,
        updated_at=now,
    )
    db.add(workflow)
    db.flush()

    _run_validation(workflow)
    workflow.updated_at = now

    return _workflow_to_response(workflow)


@comfyui_router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: DbSession) -> WorkflowResponse:
    workflow = db.get(ComfyUIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")
    return _workflow_to_response(workflow)


@comfyui_router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(workflow_id: int, body: WorkflowUpdateRequest, db: DbSession) -> WorkflowResponse:
    workflow = db.get(ComfyUIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    if body.name is not None:
        workflow.name = body.name
    if body.category is not None:
        workflow.category = body.category
    if body.inputs is not None:
        workflow.inputs = [inp.model_dump() for inp in body.inputs]
    if body.params is not None:
        workflow.params = [param.model_dump() for param in body.params]

    _run_validation(workflow)
    workflow.updated_at = datetime.now(UTC).replace(tzinfo=None)

    return _workflow_to_response(workflow)


@comfyui_router.delete("/workflows/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: int, db: DbSession) -> None:
    workflow = db.get(ComfyUIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    template_path = Path(workflow.template_path)
    db.delete(workflow)
    db.flush()

    if template_path.exists():
        try:
            template_path.unlink()
        except OSError:
            log.warning("Could not delete template file: %s", template_path)


# -- Introspection ------------------------------------------------------------

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


# -- Activation / Deactivation -----------------------------------------------

@comfyui_router.post("/workflows/{workflow_id}/activate", response_model=WorkflowResponse)
def activate_workflow(workflow_id: int, db: DbSession) -> WorkflowResponse:
    workflow = db.get(ComfyUIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    _run_validation(workflow)

    if not workflow.is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Workflow kann nicht aktiviert werden -- Validierungsfehler",
                "errors": workflow.validation_errors or [],
            },
        )

    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    if not comfyui_cfg.get("enabled", False):
        raise HTTPException(
            status_code=422,
            detail="ComfyUI-Integration ist deaktiviert -- zuerst in den Einstellungen aktivieren",
        )

    workflow.is_active = True
    workflow.updated_at = datetime.now(UTC).replace(tzinfo=None)

    return _workflow_to_response(workflow)


@comfyui_router.post("/workflows/{workflow_id}/deactivate", response_model=WorkflowResponse)
def deactivate_workflow(workflow_id: int, db: DbSession) -> WorkflowResponse:
    workflow = db.get(ComfyUIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    workflow.is_active = False
    workflow.updated_at = datetime.now(UTC).replace(tzinfo=None)

    return _workflow_to_response(workflow)


# -- Duplicate ----------------------------------------------------------------

@comfyui_router.post("/workflows/{workflow_id}/duplicate", response_model=WorkflowResponse, status_code=201)
def duplicate_workflow(workflow_id: int, db: DbSession) -> WorkflowResponse:
    original = db.get(ComfyUIWorkflow, workflow_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    src_path = Path(original.template_path)
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Template-Datei nicht gefunden")

    dest_dir = _workflows_dir()
    stem = src_path.stem
    dest_path = dest_dir / f"{stem}_copy.api.json"
    counter = 1
    while dest_path.exists():
        dest_path = dest_dir / f"{stem}_copy_{counter}.api.json"
        counter += 1

    shutil.copy2(src_path, dest_path)

    now = datetime.now(UTC).replace(tzinfo=None)
    clone = ComfyUIWorkflow(
        name=f"{original.name} (Kopie)",
        category=original.category,
        template_path=str(dest_path.resolve()),
        inputs=list(original.inputs) if original.inputs else [],
        params=list(original.params) if original.params else [],
        is_active=False,
        is_valid=original.is_valid,
        validation_errors=original.validation_errors,
        created_at=now,
        updated_at=now,
    )
    db.add(clone)
    db.flush()

    return _workflow_to_response(clone)


# -- Re-validate (template re-import / drift check) --------------------------

@comfyui_router.post("/workflows/{workflow_id}/revalidate", response_model=WorkflowResponse)
def revalidate_workflow(workflow_id: int, db: DbSession) -> WorkflowResponse:
    workflow = db.get(ComfyUIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    _run_validation(workflow)
    workflow.updated_at = datetime.now(UTC).replace(tzinfo=None)

    return _workflow_to_response(workflow)


# -- Run (Fire-and-Forget, Phase 3) ------------------------------------------

class RunRequest(BaseModel):
    inputs: dict[str, int | list[int]]
    face_inputs: dict[str, int | list[int]] = {}
    params: dict[str, Any] = {}


class RunJobDto(BaseModel):
    job_id: str


class RunResponse(BaseModel):
    jobs: list[RunJobDto]


@comfyui_router.post("/workflows/{workflow_id}/run", response_model=RunResponse)
async def run_workflow(workflow_id: int, body: RunRequest, db: DbSession) -> RunResponse:
    from photofant.jobs.comfyui_run_job import enqueue_comfyui_runs, expand_batch

    workflow = db.get(ComfyUIWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    if not workflow.is_active or not workflow.is_valid:
        raise HTTPException(
            status_code=422,
            detail="Workflow ist nicht aktiv oder nicht valide — zuerst validieren und aktivieren",
        )

    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    if not comfyui_cfg.get("enabled", False):
        raise HTTPException(
            status_code=422,
            detail="ComfyUI-Integration ist deaktiviert — zuerst in den Einstellungen aktivieren",
        )

    # Connection gate
    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui_cfg.get("timeout", 10))
    connection_client = ComfyUIClient(base_url=base_url, timeout=timeout)
    try:
        connection_client.system_stats()
    except ComfyUIError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"ComfyUI nicht erreichbar: {exc.what_found}. {exc.next_step}.",
        ) from exc

    input_bindings: list[dict[str, Any]] = workflow.inputs or []
    param_bindings: list[dict[str, Any]] = workflow.params or []

    # Validate required inputs are provided
    required_keys = {b["key"] for b in input_bindings if b.get("required", True)}
    missing = required_keys - set(body.inputs.keys())
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Pflicht-Inputs fehlen: {', '.join(sorted(missing))}",
        )

    # Validate and expand batch axis (asset inputs + face inputs)
    try:
        expanded = expand_batch(body.inputs, input_bindings, body.face_inputs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    template = _load_template(workflow.template_path)

    statuses = await enqueue_comfyui_runs(
        workflow_template=template,
        input_bindings=input_bindings,
        param_bindings=param_bindings,
        expanded_inputs=expanded,
        params=body.params,
        workflow_name=workflow.name,
    )

    return RunResponse(jobs=[RunJobDto(job_id=status.id) for status in statuses])


# -- Results (Phase 5) --------------------------------------------------------

_IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".webp"})


class ComfyUIResultItem(BaseModel):
    filename: str
    subfolder: str
    source: str  # "history" | "output_dir"
    preview_url: str


class ComfyUIResultsResponse(BaseModel):
    items: list[ComfyUIResultItem]


def _extract_history_items(history: dict[str, Any]) -> list[ComfyUIResultItem]:
    """Parse ComfyUI /history response → list of output image items."""
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
    """Walk output_dir (non-recursively) for image files, newest first."""
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

    # History path (if prompt_id given and ComfyUI reachable)
    if prompt_id:
        base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
        timeout = float(comfyui_cfg.get("timeout", 10))
        client = ComfyUIClient(base_url=base_url, timeout=timeout)
        history = client.get_history(prompt_id)
        items.extend(_extract_history_items(history))

    # output_dir scan (always, deduplication by filename)
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

    # Try ComfyUI remote first
    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui_cfg.get("timeout", 10))
    client = ComfyUIClient(base_url=base_url, timeout=timeout)
    _MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

    try:
        data = client.view_image(filename, subfolder)
        ext = Path(filename).suffix.lower()
        return _FastAPIResponse(content=data, media_type=_MEDIA_TYPES.get(ext, "image/png"))
    except ComfyUIError:
        pass

    # Fallback: read from local output_dir
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
    # -- Load asset --
    instance = db.query(AssetInstance).filter(
        AssetInstance.asset_id == body.asset_id,
        AssetInstance.deleted_at.is_(None),
    ).first()
    if instance is None:
        raise HTTPException(status_code=404, detail="Asset nicht gefunden")

    person = db.get(Person, instance.person_id)
    if person is None:
        raise HTTPException(status_code=500, detail="Person nicht gefunden")

    # -- Fetch image bytes (ComfyUI /view → fallback: output_dir) --
    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui_cfg.get("timeout", 10))
    output_dir = str(comfyui_cfg.get("output_dir", ""))

    import contextlib

    image_bytes: bytes | None = None

    client = ComfyUIClient(base_url=base_url, timeout=timeout)
    with contextlib.suppress(ComfyUIError):
        image_bytes = client.view_image(body.filename, body.subfolder)

    if image_bytes is None:
        for candidate in [
            Path(output_dir) / body.subfolder / body.filename if body.subfolder else None,
            Path(output_dir) / body.filename if output_dir else None,
        ]:
            if candidate is not None and candidate.is_file():
                image_bytes = candidate.read_bytes()
                break

    if image_bytes is None:
        raise HTTPException(
            status_code=404,
            detail=f"Datei '{body.filename}' nicht abrufbar — weder via ComfyUI noch in output_dir",
        )

    # -- Write to person/edits/ --
    data_root_path = Path(get_data_root())
    person_dir = ensure_person_folder(data_root_path, person)
    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(body.filename).suffix.lower() or ".png"
    dest_name = f"comfyui_{_uuid.uuid4().hex[:12]}{ext}"
    dest = edits_dir / dest_name
    dest.write_bytes(image_bytes)

    # -- Read dimensions --
    try:
        with _Image.open(dest) as img:
            width, height = img.size
    except Exception:
        width, height = None, None

    # -- Create Version (type=comfyui) --
    siblings = db.query(Version).filter(
        Version.instance_id == instance.id,
        Version.is_current.is_(True),
    )
    for sibling in siblings.all():
        sibling.is_current = False

    version = Version(
        instance_id=instance.id,
        face_id=None,
        type="comfyui",
        parent_id=None,
        path=str(dest.resolve()),
        is_current=True,
        params={
            "width": width,
            "height": height,
            "source": "comfyui",
            "source_filename": body.filename,
            "source_subfolder": body.subfolder,
        },
        created_at=datetime.now(UTC),
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # -- Generate thumbnails --
    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for thumb_size in (256, 512):
        try:
            thumb = await asyncio.to_thread(generate_thumbnail, dest, thumb_size)
            await asyncio.to_thread(store_thumbnail, cache_path, version.id, thumb_size, thumb, "edit")
        except Exception:
            log.warning("Thumbnail-Generierung fehlgeschlagen für %s (size %d)", dest, thumb_size)

    log.info("comfyui import: asset %d → version %d (%s)", body.asset_id, version.id, body.filename)
    return ComfyUIImportResponse(
        version_id=version.id,
        type=version.type or "comfyui",
        path=version.path,
        is_current=version.is_current,
        params=version.params,
        thumbnail_url=f"/api/versions/{version.id}/thumbnail",
    )
