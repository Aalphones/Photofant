"""ComfyUI run job — Fire-and-Forget trigger: upload → patch → prompt.

One job per batch image. Batch expansion (single axis, mask-protected) happens
at enqueue time; each queued job handles exactly one set of asset inputs.
"""
from __future__ import annotations

import asyncio
import copy
import logging
from pathlib import Path
from typing import Any

from photofant.comfyui.client import ComfyUIClient
from photofant.db.models import Asset, AssetInstance
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.settings import load_settings

log = logging.getLogger(__name__)


# ── Template patching ─────────────────────────────────────────────────────────

def _find_node_id(
    template: dict[str, Any],
    node_title: str,
    node_id: str,
) -> str | None:
    """Resolve a node by title (preferred) or id (fallback). Returns None if not found."""
    if node_title:
        matches = [
            nid
            for nid, node_data in template.items()
            if isinstance(node_data, dict)
            and isinstance(node_data.get("_meta"), dict)
            and node_data["_meta"].get("title") == node_title
        ]
        if len(matches) == 1:
            return matches[0]
    if node_id and node_id in template:
        return node_id
    return None


def patch_template(
    template: dict[str, Any],
    input_bindings: list[dict[str, Any]],
    asset_filenames: dict[str, str],
    param_bindings: list[dict[str, Any]],
    param_values: dict[str, Any],
) -> dict[str, Any]:
    """Return a deepcopy of *template* with inputs/params patched from bindings.

    asset_filenames: {key → filename returned by ComfyUI /upload/image}
    param_values:    {key → value to set on the node field}
    Original template is never mutated.
    """
    patched: dict[str, Any] = copy.deepcopy(template)

    for binding in input_bindings:
        key = binding["key"]
        filename = asset_filenames.get(key)
        if filename is None:
            continue
        resolved = _find_node_id(
            patched,
            binding.get("node_title", ""),
            binding.get("node_id", ""),
        )
        if resolved is None:
            raise ValueError(
                f"Binding '{key}': Node nicht gefunden "
                f"(title={binding.get('node_title')!r}, id={binding.get('node_id')!r})"
            )
        field = binding.get("field", "image")
        patched[resolved]["inputs"][field] = filename

    for binding in param_bindings:
        key = binding["key"]
        value = param_values.get(key)
        if value is None:
            continue
        resolved = _find_node_id(
            patched,
            binding.get("node_title", ""),
            binding.get("node_id", ""),
        )
        if resolved is None:
            raise ValueError(
                f"Param-Binding '{key}': Node nicht gefunden "
                f"(title={binding.get('node_title')!r})"
            )
        field = binding["field"]
        patched[resolved]["inputs"][field] = value

    return patched


# ── Batch expansion ───────────────────────────────────────────────────────────

def expand_batch(
    inputs: dict[str, int | list[int]],
    input_bindings: list[dict[str, Any]],
) -> list[dict[str, int]]:
    """Expand inputs into N single-asset dicts (one per batch-axis image).

    Rules:
    - At most one batch axis (array value).
    - kind=mask inputs cannot be the batch axis.
    - A second array input raises ValueError.
    - No array input → one job (pass-through).
    """
    kind_map = {b["key"]: b.get("kind", "image") for b in input_bindings}

    batch_key: str | None = None
    batch_items: list[int] = []

    for key, value in inputs.items():
        if not isinstance(value, list):
            continue
        if kind_map.get(key) == "mask":
            raise ValueError(
                f"Input '{key}' hat kind=mask und kann nicht als Batch-Achse verwendet werden."
            )
        if batch_key is not None:
            raise ValueError(
                f"Mehrere Batch-Achsen: '{batch_key}' und '{key}'. "
                "Nur ein Input darf eine Liste sein."
            )
        batch_key = key
        batch_items = value

    if batch_key is None:
        single: dict[str, int] = {
            key: (value[0] if isinstance(value, list) else value)
            for key, value in inputs.items()
        }
        return [single]

    result: list[dict[str, int]] = []
    for asset_id in batch_items:
        job_inputs: dict[str, int] = {}
        for key, value in inputs.items():
            if key == batch_key:
                job_inputs[key] = asset_id
            else:
                job_inputs[key] = value[0] if isinstance(value, list) else value  # type: ignore[assignment]
        result.append(job_inputs)
    return result


# ── Asset path resolution ─────────────────────────────────────────────────────

def _resolve_asset_paths(asset_ids: list[int]) -> dict[int, str]:
    """Return {asset_id: file_path} for active (non-deleted) instances."""
    with SessionLocal() as session:
        rows = (
            session.query(Asset.id, AssetInstance.path)
            .join(AssetInstance, AssetInstance.asset_id == Asset.id)
            .filter(Asset.id.in_(asset_ids))
            .filter(AssetInstance.deleted_at.is_(None))
            .all()
        )
    return {int(row[0]): str(row[1]) for row in rows}


# ── Job coroutine ─────────────────────────────────────────────────────────────

async def run_comfyui_run_job(
    status: JobStatus,
    workflow_template: dict[str, Any],
    input_bindings: list[dict[str, Any]],
    param_bindings: list[dict[str, Any]],
    job_inputs: dict[str, int],
    params: dict[str, Any],
    base_url: str,
    client_id: str,
    timeout: float,
) -> None:
    """Execute one ComfyUI run: upload all inputs → patch template → POST /prompt."""
    client = ComfyUIClient(base_url=base_url, timeout=timeout)

    # 1. Resolve file paths
    asset_ids = list(job_inputs.values())
    path_map = await asyncio.to_thread(_resolve_asset_paths, asset_ids)

    # 2. Upload each input image to ComfyUI; collect assigned filenames
    asset_filenames: dict[str, str] = {}
    for key, asset_id in job_inputs.items():
        file_path_str = path_map.get(asset_id)
        if file_path_str is None:
            raise ValueError(f"Asset {asset_id} nicht gefunden oder gelöscht")
        uploaded_name = await asyncio.to_thread(client.upload_image, Path(file_path_str))
        asset_filenames[key] = uploaded_name
        log.info("Uploaded asset %d as '%s' (job %s)", asset_id, uploaded_name, status.id)

    job_queue.update(status, progress=0.5, state=JobState.RUNNING)

    # 3. Patch a fresh deepcopy of the template
    patched = patch_template(
        workflow_template,
        input_bindings,
        asset_filenames,
        param_bindings,
        params,
    )

    # 4. Submit to ComfyUI
    prompt_id = await asyncio.to_thread(client.submit_prompt, patched, client_id)
    log.info("Prompt submitted: job_id=%s prompt_id=%s", status.id, prompt_id)


# ── Enqueueing ────────────────────────────────────────────────────────────────

async def enqueue_comfyui_runs(
    workflow_template: dict[str, Any],
    input_bindings: list[dict[str, Any]],
    param_bindings: list[dict[str, Any]],
    expanded_inputs: list[dict[str, int]],
    params: dict[str, Any],
    workflow_name: str,
) -> list[JobStatus]:
    """Enqueue N jobs (one per entry in *expanded_inputs*). Returns their JobStatus list."""
    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    client_id = str(comfyui_cfg.get("client_id", "photofant"))
    timeout = float(comfyui_cfg.get("timeout", 10))

    total = len(expanded_inputs)
    statuses: list[JobStatus] = []

    for index, job_inputs in enumerate(expanded_inputs):
        label = f"ComfyUI: {workflow_name}"
        if total > 1:
            label += f" ({index + 1}/{total})"

        status = await job_queue.enqueue(
            kind=JobKind.COMFYUI_RUN,
            label=label,
            coro_factory=lambda js, ji=job_inputs: run_comfyui_run_job(
                js,
                workflow_template,
                input_bindings,
                param_bindings,
                ji,
                params,
                base_url,
                client_id,
                timeout,
            ),
        )
        statuses.append(status)

    return statuses
