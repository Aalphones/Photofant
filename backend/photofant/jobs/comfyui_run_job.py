"""ComfyUI run job — Fire-and-Forget trigger: upload → patch → prompt.

One job per batch image. Batch expansion (single axis, mask-protected) happens
at enqueue time; each queued job handles exactly one set of asset inputs.
"""
from __future__ import annotations

import asyncio
import copy
import logging
from pathlib import Path
from time import monotonic
from typing import Any

from photofant.comfyui.client import ComfyUIClient
from photofant.comfyui.importer import (
    ComfyUIOutputRef,
    delete_imported_local_output,
    import_comfyui_output,
    select_output_from_history,
)
from photofant.db.models import Asset, AssetInstance, Face
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
    face_inputs: dict[str, int | list[int]] | None = None,
) -> list[tuple[dict[str, int], dict[str, int]]]:
    """Expand inputs into N (asset_inputs, face_inputs) tuples — one per batch job.

    Rules:
    - At most one batch axis across BOTH inputs and face_inputs.
    - kind=mask inputs cannot be the batch axis.
    - A second array input (in either map) raises ValueError.
    - No array input → one job (pass-through).
    """
    resolved_face_inputs: dict[str, int | list[int]] = face_inputs or {}
    kind_map = {b["key"]: b.get("kind", "image") for b in input_bindings}

    batch_key: str | None = None
    batch_in_faces = False

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
        batch_in_faces = False

    for key, value in resolved_face_inputs.items():
        if not isinstance(value, list):
            continue
        if batch_key is not None:
            raise ValueError(
                f"Mehrere Batch-Achsen: '{batch_key}' und '{key}'. "
                "Nur ein Input darf eine Liste sein."
            )
        batch_key = key
        batch_in_faces = True

    if batch_key is None:
        single_assets: dict[str, int] = {
            key: (value[0] if isinstance(value, list) else value)
            for key, value in inputs.items()
        }
        single_faces: dict[str, int] = {
            key: (value[0] if isinstance(value, list) else value)
            for key, value in resolved_face_inputs.items()
        }
        return [(single_assets, single_faces)]

    source_map = resolved_face_inputs if batch_in_faces else inputs
    batch_items: list[int] = source_map[batch_key]  # type: ignore[assignment]

    result: list[tuple[dict[str, int], dict[str, int]]] = []
    for item_id in batch_items:
        job_assets: dict[str, int] = {}
        for key, value in inputs.items():
            if key == batch_key and not batch_in_faces:
                job_assets[key] = item_id
            else:
                job_assets[key] = value[0] if isinstance(value, list) else value  # type: ignore[assignment]

        job_faces: dict[str, int] = {}
        for key, value in resolved_face_inputs.items():
            if key == batch_key and batch_in_faces:
                job_faces[key] = item_id
            else:
                job_faces[key] = value[0] if isinstance(value, list) else value  # type: ignore[assignment]

        result.append((job_assets, job_faces))
    return result


# ── Asset / Face path resolution ──────────────────────────────────────────────

def _resolve_asset_paths(asset_ids: list[int]) -> dict[int, str]:
    """Return {asset_id: file_path} for active (non-deleted) instances."""
    if not asset_ids:
        return {}
    with SessionLocal() as session:
        rows = (
            session.query(Asset.id, AssetInstance.path)
            .join(AssetInstance, AssetInstance.asset_id == Asset.id)
            .filter(Asset.id.in_(asset_ids))
            .filter(AssetInstance.deleted_at.is_(None))
            .all()
        )
    return {int(row[0]): str(row[1]) for row in rows}


def _resolve_face_paths(face_ids: list[int]) -> dict[int, str]:
    """Return {face_id: crop_path} for the given face IDs."""
    if not face_ids:
        return {}
    with SessionLocal() as session:
        rows = (
            session.query(Face.id, Face.crop_path)
            .filter(Face.id.in_(face_ids))
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
    job_face_inputs: dict[str, int],
    params: dict[str, Any],
    base_url: str,
    client_id: str,
    timeout: float,
    mask_input_key: str | None = None,
    mask_data_url: str | None = None,
    auto_import: dict[str, Any] | None = None,
) -> None:
    """Execute one ComfyUI run: upload all inputs → patch template → POST /prompt.

    If mask_input_key and mask_data_url are set, the asset for that key is combined
    with the mask canvas (RGBA embedding) before upload — Flux-Fill alpha convention.
    """
    from photofant.media.alpha_mask import embed_mask_as_alpha

    client = ComfyUIClient(base_url=base_url, timeout=timeout)

    # 1. Resolve file paths for assets and faces
    path_map = await asyncio.to_thread(_resolve_asset_paths, list(job_inputs.values()))
    face_path_map = await asyncio.to_thread(_resolve_face_paths, list(job_face_inputs.values()))

    # 2. Upload each input image to ComfyUI; collect assigned filenames
    asset_filenames: dict[str, str] = {}
    for key, asset_id in job_inputs.items():
        file_path_str = path_map.get(asset_id)
        if file_path_str is None:
            raise ValueError(f"Asset {asset_id} nicht gefunden oder gelöscht")

        if key == mask_input_key and mask_data_url:
            image_bytes = await asyncio.to_thread(Path(file_path_str).read_bytes)
            rgba_bytes = await asyncio.to_thread(embed_mask_as_alpha, image_bytes, mask_data_url)
            uploaded_name = await asyncio.to_thread(
                client.upload_image_bytes, rgba_bytes, "mask_embed.png"
            )
            log.info("Uploaded alpha-masked asset %d as '%s' (job %s)", asset_id, uploaded_name, status.id)
        else:
            uploaded_name = await asyncio.to_thread(client.upload_image, Path(file_path_str))
            log.info("Uploaded asset %d as '%s' (job %s)", asset_id, uploaded_name, status.id)

        asset_filenames[key] = uploaded_name

    for key, face_id in job_face_inputs.items():
        file_path_str = face_path_map.get(face_id)
        if file_path_str is None:
            raise ValueError(f"Gesicht {face_id} nicht gefunden")
        uploaded_name = await asyncio.to_thread(client.upload_image, Path(file_path_str))
        asset_filenames[key] = uploaded_name
        log.info("Uploaded face %d as '%s' (job %s)", face_id, uploaded_name, status.id)

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

    if auto_import is not None:
        await _wait_and_import_output(
            status=status,
            client=client,
            prompt_id=prompt_id,
            auto_import=auto_import,
        )


async def _wait_and_import_output(
    status: JobStatus,
    client: ComfyUIClient,
    prompt_id: str,
    auto_import: dict[str, Any],
) -> None:
    output_node_id = str(auto_import["output_node_id"])
    poll_interval_seconds = float(auto_import["poll_interval_seconds"])
    wait_timeout_seconds = float(auto_import["wait_timeout_seconds"])
    output_dir = str(auto_import["output_dir"])
    target_asset_id = int(auto_import["target_asset_id"])
    workflow_key = str(auto_import["workflow_key"])
    task = str(auto_import["task"])

    job_queue.update(status, progress=0.6, state=JobState.RUNNING)
    deadline = monotonic() + wait_timeout_seconds
    output: ComfyUIOutputRef | None = None

    while monotonic() < deadline:
        history = await asyncio.to_thread(client.get_history, prompt_id)
        try:
            output = select_output_from_history(history, prompt_id, output_node_id)
            break
        except ValueError:
            remaining = max(deadline - monotonic(), 0.0)
            progress = 0.6 + 0.25 * (1.0 - (remaining / wait_timeout_seconds))
            job_queue.update(status, progress=min(progress, 0.85), state=JobState.RUNNING)
            await asyncio.sleep(poll_interval_seconds)

    if output is None:
        raise TimeoutError(f"Timeout beim Warten auf ComfyUI-Output fuer Prompt {prompt_id}")

    job_queue.update(status, progress=0.9, state=JobState.RUNNING)
    await asyncio.to_thread(
        _import_and_cleanup,
        client,
        target_asset_id,
        output,
        output_dir,
        task,
        workflow_key,
        prompt_id,
    )


def _import_and_cleanup(
    client: ComfyUIClient,
    target_asset_id: int,
    output: ComfyUIOutputRef,
    output_dir: str,
    task: str,
    workflow_key: str,
    prompt_id: str,
) -> None:
    with SessionLocal() as session:
        import_comfyui_output(
            session,
            client,
            asset_id=target_asset_id,
            output=output,
            output_dir=output_dir,
            params={
                "source": "comfyui_auto_import",
                "task": task,
                "workflow_key": workflow_key,
                "prompt_id": prompt_id,
            },
        )
    delete_imported_local_output(output_dir, output)


# ── Enqueueing ────────────────────────────────────────────────────────────────

async def enqueue_comfyui_runs(
    workflow_template: dict[str, Any],
    input_bindings: list[dict[str, Any]],
    param_bindings: list[dict[str, Any]],
    expanded_inputs: list[tuple[dict[str, int], dict[str, int]]],
    params: dict[str, Any],
    workflow_name: str,
    mask_input_key: str | None = None,
    mask_data_url: str | None = None,
    auto_import_targets: list[int] | None = None,
    auto_import_task: str | None = None,
    auto_import_workflow_key: str | None = None,
    auto_import_output_node_id: str | None = None,
) -> list[JobStatus]:
    """Enqueue N jobs (one per entry in *expanded_inputs*). Returns their JobStatus list."""
    cfg = load_settings()
    comfyui_cfg = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    base_url = str(comfyui_cfg.get("base_url", "http://127.0.0.1:8188"))
    client_id = str(comfyui_cfg.get("client_id", "photofant"))
    timeout = float(comfyui_cfg.get("timeout", 10))
    output_dir = str(comfyui_cfg.get("output_dir", ""))
    poll_interval_seconds = float(comfyui_cfg.get("result_poll_interval_seconds", 1.0))
    wait_timeout_seconds = float(comfyui_cfg.get("result_wait_timeout_seconds", 1800))

    total = len(expanded_inputs)
    statuses: list[JobStatus] = []

    for index, (job_inputs, job_face_inputs) in enumerate(expanded_inputs):
        label = f"ComfyUI: {workflow_name}"
        if total > 1:
            label += f" ({index + 1}/{total})"

        auto_import: dict[str, Any] | None = None
        if auto_import_targets is not None:
            auto_import = {
                "target_asset_id": auto_import_targets[index],
                "task": auto_import_task,
                "workflow_key": auto_import_workflow_key,
                "output_node_id": auto_import_output_node_id,
                "output_dir": output_dir,
                "poll_interval_seconds": poll_interval_seconds,
                "wait_timeout_seconds": wait_timeout_seconds,
            }

        status = await job_queue.enqueue(
            kind=JobKind.COMFYUI_RUN,
            label=label,
            coro_factory=lambda js, ji=job_inputs, jfi=job_face_inputs, ai=auto_import: run_comfyui_run_job(
                js,
                workflow_template,
                input_bindings,
                param_bindings,
                ji,
                jfi,
                params,
                base_url,
                client_id,
                timeout,
                mask_input_key=mask_input_key,
                mask_data_url=mask_data_url,
                auto_import=ai,
            ),
        )
        statuses.append(status)

    return statuses
