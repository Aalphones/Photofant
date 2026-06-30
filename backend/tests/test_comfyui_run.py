"""Tests for ComfyUI run job — Phase 3.

Covers:
- patch_template: original unchanged, deepcopy correctly patched, node lookup by title/id
- expand_batch: no batch, single axis, multi-image batch, constant unchanged,
  mask rejection, two-axes rejection
- run_comfyui_run_job: upload+prompt called, template not mutated, errors propagate
"""
from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pytest

from photofant.comfyui.client import ComfyUIError
from photofant.jobs.comfyui_run_job import expand_batch, patch_template

# ── Fixtures ──────────────────────────────────────────────────────────────────

UPSCALE_TEMPLATE = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {"image": "placeholder.png", "upload": "image"},
        "_meta": {"title": "Source"},
    },
    "2": {
        "class_type": "ImageUpscaleWithModel",
        "inputs": {"upscale_model": ["3", 0], "image": ["1", 0], "scale_by": 4.0},
        "_meta": {"title": "Upscale"},
    },
    "3": {
        "class_type": "UpscaleModelLoader",
        "inputs": {"model_name": "4x_NMKD.pth"},
        "_meta": {"title": "Model Loader"},
    },
    "4": {
        "class_type": "SaveImage",
        "inputs": {"images": ["2", 0], "filename_prefix": "photofant/upscale"},
        "_meta": {"title": "Save"},
    },
}

INPUT_BINDINGS = [
    {
        "key": "source",
        "node_title": "Source",
        "node_id": "1",
        "field": "image",
        "kind": "image",
        "required": True,
    },
]

PARAM_BINDINGS = [
    {
        "key": "scale",
        "node_title": "Upscale",
        "node_id": "2",
        "field": "scale_by",
        "type": "float",
    },
]

MULTI_INPUT_BINDINGS = [
    {"key": "reference", "node_title": "Reference", "field": "image", "kind": "image", "required": True},
    {"key": "source", "node_title": "Source", "field": "image", "kind": "image", "required": True},
]

MASK_BINDINGS = [
    {"key": "mask", "node_title": "Mask", "field": "image", "kind": "mask", "required": True},
]


# ── patch_template ─────────────────────────────────────────────────────────────

class TestPatchTemplate:
    def test_original_not_mutated(self) -> None:
        original_snapshot = copy.deepcopy(UPSCALE_TEMPLATE)
        patch_template(UPSCALE_TEMPLATE, INPUT_BINDINGS, {"source": "new.png"}, [], {})
        assert original_snapshot == UPSCALE_TEMPLATE

    def test_input_patched_via_title(self) -> None:
        patched = patch_template(
            UPSCALE_TEMPLATE, INPUT_BINDINGS, {"source": "my_image.png"}, [], {}
        )
        assert patched["1"]["inputs"]["image"] == "my_image.png"

    def test_param_patched_via_title(self) -> None:
        patched = patch_template(UPSCALE_TEMPLATE, [], {}, PARAM_BINDINGS, {"scale": 2.0})
        assert patched["2"]["inputs"]["scale_by"] == 2.0

    def test_node_id_fallback(self) -> None:
        bindings_id_only = [
            {"key": "source", "node_title": "", "node_id": "1", "field": "image"},
        ]
        patched = patch_template(
            UPSCALE_TEMPLATE, bindings_id_only, {"source": "fallback.png"}, [], {}
        )
        assert patched["1"]["inputs"]["image"] == "fallback.png"

    def test_missing_key_in_filenames_skips_node(self) -> None:
        patched = patch_template(UPSCALE_TEMPLATE, INPUT_BINDINGS, {}, [], {})
        assert patched["1"]["inputs"]["image"] == "placeholder.png"

    def test_unknown_node_title_raises(self) -> None:
        bad = [{"key": "source", "node_title": "Ghost", "node_id": "", "field": "image"}]
        with pytest.raises(ValueError, match="Node nicht gefunden"):
            patch_template(UPSCALE_TEMPLATE, bad, {"source": "x.png"}, [], {})

    def test_both_input_and_param_patched(self) -> None:
        patched = patch_template(
            UPSCALE_TEMPLATE,
            INPUT_BINDINGS,
            {"source": "my.png"},
            PARAM_BINDINGS,
            {"scale": 8.0},
        )
        assert patched["1"]["inputs"]["image"] == "my.png"
        assert patched["2"]["inputs"]["scale_by"] == 8.0


# ── expand_batch ──────────────────────────────────────────────────────────────

class TestExpandBatch:
    def test_single_scalar_input_gives_one_job(self) -> None:
        expanded = expand_batch({"source": 42}, INPUT_BINDINGS)
        assert expanded == [({"source": 42}, {})]

    def test_list_input_gives_n_jobs(self) -> None:
        expanded = expand_batch({"source": [10, 20, 30]}, INPUT_BINDINGS)
        assert len(expanded) == 3
        assert [asset_inputs["source"] for asset_inputs, _face_inputs in expanded] == [10, 20, 30]

    def test_constant_unchanged_across_batch(self) -> None:
        expanded = expand_batch({"reference": 99, "source": [1, 2, 3]}, MULTI_INPUT_BINDINGS)
        assert len(expanded) == 3
        for asset_inputs, _face_inputs in expanded:
            assert asset_inputs["reference"] == 99

    def test_batch_axis_varies_per_job(self) -> None:
        expanded = expand_batch({"reference": 99, "source": [1, 2, 3]}, MULTI_INPUT_BINDINGS)
        assert [asset_inputs["source"] for asset_inputs, _face_inputs in expanded] == [1, 2, 3]

    def test_mask_input_not_batchable(self) -> None:
        with pytest.raises(ValueError, match="kind=mask"):
            expand_batch({"mask": [1, 2]}, MASK_BINDINGS)

    def test_two_array_inputs_raises(self) -> None:
        with pytest.raises(ValueError, match="Mehrere Batch-Achsen"):
            expand_batch({"source": [1, 2], "reference": [3, 4]}, MULTI_INPUT_BINDINGS)

    def test_empty_batch_list_gives_empty_result(self) -> None:
        expanded = expand_batch({"source": []}, INPUT_BINDINGS)
        assert expanded == []

    def test_no_bindings_still_works(self) -> None:
        # No kind_map info — should still expand normally
        expanded = expand_batch({"source": [5, 6]}, [])
        assert len(expanded) == 2


# ── run_comfyui_run_job (worker) ───────────────────────────────────────────────

class TestComfyUIRunWorker:
    @pytest.mark.asyncio
    async def test_success_path_calls_upload_and_prompt(self) -> None:
        from photofant.jobs.comfyui_run_job import run_comfyui_run_job
        from photofant.jobs.queue import JobKind, JobStatus

        status = JobStatus(id="job-1", kind=JobKind.COMFYUI_RUN, label="Test")
        original_snapshot = copy.deepcopy(UPSCALE_TEMPLATE)

        with (
            patch(
                "photofant.jobs.comfyui_run_job._resolve_asset_paths",
                return_value={42: "/data/img.png"},
            ),
            patch("photofant.jobs.comfyui_run_job.ComfyUIClient") as mock_cls,
        ):
            mock_client = MagicMock()
            mock_client.upload_image.return_value = "uploaded_img.png"
            mock_client.submit_prompt.return_value = "abc-prompt-id"
            mock_cls.return_value = mock_client

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

        # DONE is set by the queue worker after the coroutine returns — not by the function itself
        mock_client.upload_image.assert_called_once()
        mock_client.submit_prompt.assert_called_once()
        # Verify template was not mutated by the job
        assert original_snapshot == UPSCALE_TEMPLATE

    @pytest.mark.asyncio
    async def test_upload_error_propagates(self) -> None:
        from photofant.jobs.comfyui_run_job import run_comfyui_run_job
        from photofant.jobs.queue import JobKind, JobStatus

        status = JobStatus(id="job-2", kind=JobKind.COMFYUI_RUN, label="Test")

        with (
            patch(
                "photofant.jobs.comfyui_run_job._resolve_asset_paths",
                return_value={42: "/data/img.png"},
            ),
            patch("photofant.jobs.comfyui_run_job.ComfyUIClient") as mock_cls,
        ):
            mock_client = MagicMock()
            mock_client.upload_image.side_effect = ComfyUIError(
                what_expected="Upload",
                what_found="Verbindung abgelehnt",
                next_step="Check",
            )
            mock_cls.return_value = mock_client

            with pytest.raises(ComfyUIError):
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
            # prompt must not have been called when upload fails
            mock_client.submit_prompt.assert_not_called()

    @pytest.mark.asyncio
    async def test_prompt_error_propagates(self) -> None:
        from photofant.jobs.comfyui_run_job import run_comfyui_run_job
        from photofant.jobs.queue import JobKind, JobStatus

        status = JobStatus(id="job-3", kind=JobKind.COMFYUI_RUN, label="Test")

        with (
            patch(
                "photofant.jobs.comfyui_run_job._resolve_asset_paths",
                return_value={42: "/data/img.png"},
            ),
            patch("photofant.jobs.comfyui_run_job.ComfyUIClient") as mock_cls,
        ):
            mock_client = MagicMock()
            mock_client.upload_image.return_value = "ok.png"
            mock_client.submit_prompt.side_effect = ComfyUIError(
                what_expected="Prompt",
                what_found="HTTP 500",
                next_step="Check logs",
            )
            mock_cls.return_value = mock_client

            with pytest.raises(ComfyUIError):
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

    @pytest.mark.asyncio
    async def test_missing_asset_raises(self) -> None:
        from photofant.jobs.comfyui_run_job import run_comfyui_run_job
        from photofant.jobs.queue import JobKind, JobStatus

        status = JobStatus(id="job-4", kind=JobKind.COMFYUI_RUN, label="Test")

        with (
            patch(
                "photofant.jobs.comfyui_run_job._resolve_asset_paths",
                return_value={},  # asset not found
            ),
            patch("photofant.jobs.comfyui_run_job.ComfyUIClient"),
            pytest.raises(ValueError, match="nicht gefunden"),
        ):
            await run_comfyui_run_job(
                    status=status,
                    workflow_template=UPSCALE_TEMPLATE,
                    input_bindings=INPUT_BINDINGS,
                    param_bindings=[],
                    job_inputs={"source": 999},
                    job_face_inputs={},
                    params={},
                    base_url="http://127.0.0.1:8188",
                    client_id="photofant",
                    timeout=10.0,
                )

    @pytest.mark.asyncio
    async def test_param_patched_in_prompt(self) -> None:
        """Params are visible in the prompt payload sent to ComfyUI."""
        from photofant.jobs.comfyui_run_job import run_comfyui_run_job
        from photofant.jobs.queue import JobKind, JobStatus

        status = JobStatus(id="job-5", kind=JobKind.COMFYUI_RUN, label="Test")
        captured_prompt: dict = {}

        def capture_submit(prompt: dict, client_id: str = "photofant") -> str:
            captured_prompt.update(prompt)
            return "pid-123"

        with (
            patch(
                "photofant.jobs.comfyui_run_job._resolve_asset_paths",
                return_value={42: "/data/img.png"},
            ),
            patch("photofant.jobs.comfyui_run_job.ComfyUIClient") as mock_cls,
        ):
            mock_client = MagicMock()
            mock_client.upload_image.return_value = "img.png"
            mock_client.submit_prompt.side_effect = capture_submit
            mock_cls.return_value = mock_client

            await run_comfyui_run_job(
                status=status,
                workflow_template=UPSCALE_TEMPLATE,
                input_bindings=INPUT_BINDINGS,
                param_bindings=PARAM_BINDINGS,
                job_inputs={"source": 42},
                job_face_inputs={},
                params={"scale": 2.0},
                base_url="http://127.0.0.1:8188",
                client_id="photofant",
                timeout=10.0,
            )

        # scale_by was patched in node "2"
        assert captured_prompt["2"]["inputs"]["scale_by"] == 2.0
        # image was patched from upload
        assert captured_prompt["1"]["inputs"]["image"] == "img.png"
