"""Tests for ComfyUI default auto-import behavior."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from photofant.comfyui.importer import (
    ComfyUIOutputRef,
    delete_imported_local_output,
    resolve_local_output_path,
    select_default_output_node_id,
)
from photofant.jobs.queue import JobKind, JobStatus


def test_marked_output_node_wins_over_other_save_nodes() -> None:
    template = {
        "4": {"class_type": "SaveImage", "_meta": {"title": "Preview"}, "inputs": {}},
        "9": {"class_type": "SaveImage", "_meta": {"title": "Photofant Output"}, "inputs": {}},
    }

    assert select_default_output_node_id(template) == "9"


def test_multiple_unmarked_outputs_block_default_import() -> None:
    template = {
        "4": {"class_type": "SaveImage", "_meta": {"title": "A"}, "inputs": {}},
        "9": {"class_type": "SaveImage", "_meta": {"title": "B"}, "inputs": {}},
    }

    with pytest.raises(ValueError, match="mehrere unmarkierte Outputs"):
        select_default_output_node_id(template)


def test_cleanup_refuses_path_outside_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    outside_dir = tmp_path / "outside"
    output_dir.mkdir()
    outside_dir.mkdir()
    outside_file = outside_dir / "result.png"
    outside_file.write_bytes(b"x")

    resolved = resolve_local_output_path(str(output_dir), "result.png", "../outside")

    assert resolved is None
    assert outside_file.exists()


def test_cleanup_deletes_local_output_inside_output_dir(tmp_path: Path) -> None:
    output_file = tmp_path / "result.png"
    output_file.write_bytes(b"x")

    deleted = delete_imported_local_output(str(tmp_path), ComfyUIOutputRef(filename="result.png"))

    assert deleted is True
    assert not output_file.exists()


@pytest.mark.asyncio
async def test_generic_run_does_not_import() -> None:
    from photofant.jobs.comfyui_run_job import run_comfyui_run_job
    from tests.test_comfyui_run import INPUT_BINDINGS, UPSCALE_TEMPLATE

    status = JobStatus(id="job-generic", kind=JobKind.COMFYUI_RUN, label="Test")

    with (
        patch("photofant.jobs.comfyui_run_job._resolve_asset_paths", return_value={42: "/data/img.png"}),
        patch("photofant.jobs.comfyui_run_job.ComfyUIClient") as mock_client_cls,
        patch("photofant.jobs.comfyui_run_job._import_and_cleanup") as import_and_cleanup,
    ):
        mock_client = MagicMock()
        mock_client.upload_image.return_value = "uploaded.png"
        mock_client.submit_prompt.return_value = "prompt-1"
        mock_client_cls.return_value = mock_client

        await run_comfyui_run_job(
            status=status,
            workflow_template=UPSCALE_TEMPLATE,
            input_bindings=INPUT_BINDINGS,
            param_bindings=[],
            job_inputs={"source": 42},
            job_face_inputs={},
            params={},
            base_url="http://127.0.0.1:8188",
            client_id="photofant",
            timeout=10.0,
        )

    import_and_cleanup.assert_not_called()


@pytest.mark.asyncio
async def test_default_run_imports_history_output() -> None:
    from photofant.jobs.comfyui_run_job import run_comfyui_run_job
    from tests.test_comfyui_run import INPUT_BINDINGS, UPSCALE_TEMPLATE

    status = JobStatus(id="job-auto", kind=JobKind.COMFYUI_RUN, label="Test")
    history = {
        "prompt-1": {
            "outputs": {
                "4": {
                    "images": [
                        {"filename": "result.png", "subfolder": "", "width": 32, "height": 32},
                    ],
                },
            },
        },
    }

    imported_stub = SimpleNamespace(asset_id=101, path="/data/edits/img.png")

    with (
        patch("photofant.jobs.comfyui_run_job._resolve_asset_paths", return_value={42: "/data/img.png"}),
        patch("photofant.jobs.comfyui_run_job.ComfyUIClient") as mock_client_cls,
        patch("photofant.jobs.comfyui_run_job._import_and_cleanup", return_value=imported_stub) as import_and_cleanup,
        patch("photofant.jobs.import_job.enqueue_post_import_pipeline", new_callable=AsyncMock) as enqueue_pipeline,
    ):
        mock_client = MagicMock()
        mock_client.upload_image.return_value = "uploaded.png"
        mock_client.submit_prompt.return_value = "prompt-1"
        mock_client.get_history.return_value = history
        mock_client_cls.return_value = mock_client

        await run_comfyui_run_job(
            status=status,
            workflow_template=UPSCALE_TEMPLATE,
            input_bindings=INPUT_BINDINGS,
            param_bindings=[],
            job_inputs={"source": 42},
            job_face_inputs={},
            params={},
            base_url="http://127.0.0.1:8188",
            client_id="photofant",
            timeout=10.0,
            auto_import={
                "target_asset_id": 99,
                "task": "upscale",
                "workflow_key": "default_upscale",
                "output_node_id": "4",
                "output_dir": "",
                "poll_interval_seconds": 0.01,
                "wait_timeout_seconds": 1,
            },
        )

    import_and_cleanup.assert_called_once()
    assert import_and_cleanup.call_args.args[1] == 99
    assert import_and_cleanup.call_args.args[2].filename == "result.png"
    # ADR-013: a successful import must trigger the normal post-import pipeline
    # (tagging/caption/face/embedding) since the result is now a full Asset.
    enqueue_pipeline.assert_called_once_with([101])


@pytest.mark.asyncio
async def test_default_route_rejects_bulk_target_count_mismatch(tmp_path: Path) -> None:
    from photofant.api.comfyui import DefaultRunRequest, run_default_workflow

    workflow_path = tmp_path / "wf.json"
    workflow_path.write_text("{}", encoding="utf-8")
    suggestion = SimpleNamespace(
        key="source",
        label="Source",
        node_title="Source",
        node_id="1",
        field="image",
        kind="image",
        required=True,
        lockable=False,
    )
    introspection = SimpleNamespace(
        input_suggestions=[suggestion],
        mask=None,
        prompt=None,
        negative_prompt=None,
        resolution=None,
    )

    with (
        patch("photofant.api.comfyui._get_comfyui_client", return_value=(MagicMock(), {"default_upscale": "wf"})),
        patch("photofant.api.comfyui._check_connection"),
        patch("photofant.api.comfyui._workflows_dir", return_value=tmp_path),
        patch("photofant.api.comfyui.load_workflow", return_value=SimpleNamespace(is_valid=True, name="WF", errors=[])),
        patch(
            "photofant.api.comfyui.load_workflow_template",
            return_value={
                "4": {"class_type": "SaveImage", "_meta": {"title": "Photofant Output"}, "inputs": {}},
            },
        ),
        patch("photofant.comfyui.introspect.load_and_introspect", return_value=introspection),
        pytest.raises(HTTPException) as exc_info,
    ):
        await run_default_workflow(
            "upscale",
            DefaultRunRequest(inputs={"source": [1, 2]}, target_asset_ids=[1]),
        )

    assert exc_info.value.status_code == 422
    assert "target_asset_ids" in str(exc_info.value.detail)
