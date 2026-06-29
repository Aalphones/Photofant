"""Tests für FS-Discovery (scan_workflows) und Alpha-Mask-Embedding (P16 Phase 2)."""
from __future__ import annotations

import base64
import io
import json

from PIL import Image

from photofant.comfyui.discovery import load_workflow, load_workflow_template, scan_workflows

# ── Test fixtures ─────────────────────────────────────────────────────────────

UPSCALE_TEMPLATE = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {"image": "placeholder.png", "upload": "image"},
        "_meta": {"title": "Source"},
    },
    "2": {
        "class_type": "ImageUpscaleWithModel",
        "inputs": {"upscale_model": ["3", 0], "image": ["1", 0]},
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

FLUX_EDIT_TEMPLATE = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {"image": "placeholder.png"},
        "_meta": {"title": "Source"},
    },
    "2": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "", "clip": ["99", 0]},
        "_meta": {"title": "Positive Prompt"},
    },
    "3": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "", "clip": ["99", 0]},
        "_meta": {"title": "Negative Prompt"},
    },
    "4": {
        "class_type": "SaveImage",
        "inputs": {"images": ["5", 0], "filename_prefix": "photofant/edit"},
        "_meta": {"title": "Save"},
    },
}


# ── scan_workflows ─────────────────────────────────────────────────────────────

class TestScanWorkflows:
    def test_empty_dir_returns_empty(self, tmp_path) -> None:
        assert scan_workflows(tmp_path) == []

    def test_missing_dir_returns_empty(self, tmp_path) -> None:
        assert scan_workflows(tmp_path / "nonexistent") == []

    def test_scans_json_files(self, tmp_path) -> None:
        (tmp_path / "upscale.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert len(items) == 1
        assert items[0].key == "upscale"
        assert items[0].name == "Upscale"

    def test_api_json_beats_plain_json(self, tmp_path) -> None:
        (tmp_path / "upscale.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        (tmp_path / "upscale.api.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert len(items) == 1
        assert items[0].key == "upscale"

    def test_category_detected(self, tmp_path) -> None:
        (tmp_path / "upscale.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert items[0].category == "upscale"

    def test_is_valid_true_for_complete_workflow(self, tmp_path) -> None:
        (tmp_path / "upscale.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert items[0].is_valid is True
        assert items[0].errors == []

    def test_is_valid_false_without_save_image(self, tmp_path) -> None:
        no_save = {k: v for k, v in UPSCALE_TEMPLATE.items() if k != "4"}
        (tmp_path / "bad.json").write_text(json.dumps(no_save), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert items[0].is_valid is False
        assert len(items[0].errors) > 0

    def test_inputs_extracted(self, tmp_path) -> None:
        (tmp_path / "upscale.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert len(items[0].inputs) == 1
        assert items[0].inputs[0]["key"] == "source"
        assert items[0].inputs[0]["kind"] == "image"

    def test_prompt_detected(self, tmp_path) -> None:
        (tmp_path / "edit.json").write_text(json.dumps(FLUX_EDIT_TEMPLATE), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert items[0].prompt is not None
        assert items[0].negative_prompt is not None

    def test_sorted_by_name(self, tmp_path) -> None:
        (tmp_path / "zebra.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        (tmp_path / "alpha.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert items[0].name == "Alpha"
        assert items[1].name == "Zebra"

    def test_invalid_json_does_not_crash(self, tmp_path) -> None:
        (tmp_path / "broken.json").write_text("not-json", encoding="utf-8")
        items = scan_workflows(tmp_path)
        assert len(items) == 1
        assert items[0].is_valid is False

    def test_non_json_files_ignored(self, tmp_path) -> None:
        (tmp_path / "readme.txt").write_text("ignore me", encoding="utf-8")
        assert scan_workflows(tmp_path) == []


# ── load_workflow / load_workflow_template ─────────────────────────────────────

class TestLoadWorkflow:
    def test_load_existing_workflow(self, tmp_path) -> None:
        (tmp_path / "upscale.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        item = load_workflow(tmp_path, "upscale")
        assert item is not None
        assert item.key == "upscale"

    def test_load_missing_workflow_returns_none(self, tmp_path) -> None:
        assert load_workflow(tmp_path, "nonexistent") is None

    def test_load_template_dict(self, tmp_path) -> None:
        (tmp_path / "upscale.api.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        template = load_workflow_template(tmp_path, "upscale")
        assert template is not None
        assert "1" in template

    def test_api_json_preferred_for_template(self, tmp_path) -> None:
        modified = {**UPSCALE_TEMPLATE, "extra_key": {"class_type": "ExtraNode", "inputs": {}}}
        (tmp_path / "upscale.json").write_text(json.dumps(UPSCALE_TEMPLATE), encoding="utf-8")
        (tmp_path / "upscale.api.json").write_text(json.dumps(modified), encoding="utf-8")
        template = load_workflow_template(tmp_path, "upscale")
        assert "extra_key" in template  # type: ignore[operator]


# ── Alpha-mask embedding ───────────────────────────────────────────────────────

def _make_png_bytes(width: int, height: int, color: tuple[int, int, int, int] = (128, 64, 32, 255)) -> bytes:
    img = Image.new("RGBA", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_mask_data_url(width: int, height: int, *, mask_region: tuple[int, int, int, int] | None = None) -> str:
    """Create a mask PNG (white stroke on black bg). mask_region = (x0, y0, x1, y1)."""
    img = Image.new("L", (width, height), 0)
    if mask_region:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle(mask_region, fill=255)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"


class TestEmbedMaskAsAlpha:
    def test_masked_area_becomes_transparent(self) -> None:
        from photofant.media.alpha_mask import embed_mask_as_alpha

        source = _make_png_bytes(100, 100, (200, 100, 50, 255))
        # Mask the top-left 50×50 quadrant
        mask_data_url = _make_mask_data_url(100, 100, mask_region=(0, 0, 49, 49))

        result_bytes = embed_mask_as_alpha(source, mask_data_url)
        result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

        # Masked pixel → transparent
        masked_pixel = result.getpixel((25, 25))
        assert masked_pixel[3] == 0, f"Expected alpha=0 in masked area, got {masked_pixel[3]}"

        # Unmasked pixel → opaque
        unmasked_pixel = result.getpixel((75, 75))
        assert unmasked_pixel[3] == 255, f"Expected alpha=255 in unmasked area, got {unmasked_pixel[3]}"

    def test_rgb_values_preserved(self) -> None:
        from photofant.media.alpha_mask import embed_mask_as_alpha

        source = _make_png_bytes(50, 50, (200, 100, 50, 255))
        mask_data_url = _make_mask_data_url(50, 50)  # all black = no masking

        result_bytes = embed_mask_as_alpha(source, mask_data_url)
        result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

        pixel = result.getpixel((25, 25))
        assert pixel[0] == 200
        assert pixel[1] == 100
        assert pixel[2] == 50

    def test_output_is_rgba_png(self) -> None:
        from photofant.media.alpha_mask import embed_mask_as_alpha

        source = _make_png_bytes(20, 20)
        mask_data_url = _make_mask_data_url(20, 20)
        result_bytes = embed_mask_as_alpha(source, mask_data_url)

        result = Image.open(io.BytesIO(result_bytes))
        assert result.mode == "RGBA"

    def test_mask_resized_if_different_size(self) -> None:
        from photofant.media.alpha_mask import embed_mask_as_alpha

        source = _make_png_bytes(100, 100)
        mask_data_url = _make_mask_data_url(50, 50, mask_region=(0, 0, 49, 49))
        # Should not raise
        result_bytes = embed_mask_as_alpha(source, mask_data_url)
        result = Image.open(io.BytesIO(result_bytes))
        assert result.size == (100, 100)

    def test_data_url_without_prefix(self) -> None:
        from photofant.media.alpha_mask import embed_mask_as_alpha

        source = _make_png_bytes(20, 20)
        buf = io.BytesIO()
        Image.new("L", (20, 20), 0).save(buf, format="PNG")
        raw_b64 = base64.b64encode(buf.getvalue()).decode()
        # No "data:image/png;base64," prefix — should still work
        result_bytes = embed_mask_as_alpha(source, raw_b64)
        result = Image.open(io.BytesIO(result_bytes))
        assert result.mode == "RGBA"
