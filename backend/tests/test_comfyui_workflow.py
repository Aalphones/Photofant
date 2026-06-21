"""Tests for ComfyUI workflow introspection and validation (P8b Phase 2)."""
from __future__ import annotations

from photofant.comfyui.introspect import introspect_template
from photofant.comfyui.validator import validate_workflow

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
        "inputs": {"model_name": "4x_NMKD-Siax_200k.pth"},
        "_meta": {"title": "Model Loader"},
    },
    "4": {
        "class_type": "SaveImage",
        "inputs": {"images": ["2", 0], "filename_prefix": "photofant/upscale"},
        "_meta": {"title": "Save"},
    },
}

MULTI_INPUT_TEMPLATE = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {"image": "placeholder.png"},
        "_meta": {"title": "Source"},
    },
    "2": {
        "class_type": "LoadImage",
        "inputs": {"image": "placeholder.png"},
        "_meta": {"title": "Reference"},
    },
    "3": {
        "class_type": "LoadImageMask",
        "inputs": {"image": "mask.png", "channel": "alpha"},
        "_meta": {"title": "Mask"},
    },
    "4": {
        "class_type": "SaveImage",
        "inputs": {"images": ["99", 0], "filename_prefix": "out"},
        "_meta": {"title": "Output"},
    },
}

UI_FORMAT_TEMPLATE = {
    "last_node_id": 10,
    "last_link_id": 5,
    "nodes": [],
    "links": [],
}

NO_SAVE_TEMPLATE = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {"image": "test.png"},
        "_meta": {"title": "Source"},
    },
    "2": {
        "class_type": "ImageUpscaleWithModel",
        "inputs": {"image": ["1", 0]},
        "_meta": {"title": "Upscale"},
    },
}


class TestIntrospection:
    def test_upscale_template_basic(self) -> None:
        result = introspect_template(UPSCALE_TEMPLATE)
        assert result.is_api_format is True
        assert result.has_save_image is True
        assert len(result.nodes) == 4
        assert len(result.input_suggestions) == 1
        assert result.input_suggestions[0].key == "source"
        assert result.input_suggestions[0].node_title == "Source"

    def test_multi_input_template(self) -> None:
        result = introspect_template(MULTI_INPUT_TEMPLATE)
        assert len(result.input_suggestions) == 3
        keys = [suggestion.key for suggestion in result.input_suggestions]
        assert "source" in keys
        assert "reference" in keys
        assert "mask" in keys
        mask_suggestion = next(
            suggestion for suggestion in result.input_suggestions if suggestion.key == "mask"
        )
        assert mask_suggestion.kind == "mask"

    def test_ui_format_rejected(self) -> None:
        result = introspect_template(UI_FORMAT_TEMPLATE)
        assert result.is_api_format is False
        assert len(result.errors) > 0
        assert "API-Format" in result.errors[0]

    def test_no_save_image_warning(self) -> None:
        result = introspect_template(NO_SAVE_TEMPLATE)
        assert result.has_save_image is False
        assert any("SaveImage" in error for error in result.errors)

    def test_empty_template(self) -> None:
        result = introspect_template({})
        assert len(result.nodes) == 0
        assert any("Keine Nodes" in error for error in result.errors)

    def test_non_dict_rejected(self) -> None:
        result = introspect_template([1, 2, 3])  # type: ignore[arg-type]
        assert result.is_api_format is False


class TestValidation:
    def test_valid_binding_passes(self) -> None:
        inputs = [{"key": "source", "node_title": "Source", "field": "image"}]
        result = validate_workflow(UPSCALE_TEMPLATE, inputs, [])
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_title_fails(self) -> None:
        inputs = [{"key": "source", "node_title": "NonExistent", "field": "image"}]
        result = validate_workflow(UPSCALE_TEMPLATE, inputs, [])
        assert result.is_valid is False
        assert any(error.code == "title_not_found" for error in result.errors)

    def test_duplicate_title_fails(self) -> None:
        template_with_dupes = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": "a.png"},
                "_meta": {"title": "Dupe"},
            },
            "2": {
                "class_type": "LoadImage",
                "inputs": {"image": "b.png"},
                "_meta": {"title": "Dupe"},
            },
            "3": {
                "class_type": "SaveImage",
                "inputs": {"images": ["1", 0]},
                "_meta": {"title": "Save"},
            },
        }
        inputs = [{"key": "source", "node_title": "Dupe", "field": "image"}]
        result = validate_workflow(template_with_dupes, inputs, [])
        assert result.is_valid is False
        assert any(error.code == "duplicate_title" for error in result.errors)

    def test_missing_field_fails(self) -> None:
        inputs = [{"key": "source", "node_title": "Source", "field": "nonexistent_field"}]
        result = validate_workflow(UPSCALE_TEMPLATE, inputs, [])
        assert result.is_valid is False
        assert any(error.code == "field_not_found" for error in result.errors)

    def test_no_save_image_fails(self) -> None:
        result = validate_workflow(NO_SAVE_TEMPLATE, [], [])
        assert result.is_valid is False
        assert any(error.code == "no_save_image" for error in result.errors)

    def test_no_binding_target_fails(self) -> None:
        inputs = [{"key": "source", "node_title": "", "node_id": "", "field": "image"}]
        result = validate_workflow(UPSCALE_TEMPLATE, inputs, [])
        assert result.is_valid is False
        assert any(error.code == "no_binding" for error in result.errors)

    def test_param_validation(self) -> None:
        params = [{"key": "model", "node_title": "Model Loader", "field": "model_name"}]
        result = validate_workflow(UPSCALE_TEMPLATE, [], params)
        assert result.is_valid is True

    def test_node_id_fallback(self) -> None:
        inputs = [{"key": "source", "node_title": "", "node_id": "1", "field": "image"}]
        result = validate_workflow(UPSCALE_TEMPLATE, inputs, [])
        assert result.is_valid is True

    def test_invalid_node_id(self) -> None:
        inputs = [{"key": "source", "node_title": "", "node_id": "999", "field": "image"}]
        result = validate_workflow(UPSCALE_TEMPLATE, inputs, [])
        assert result.is_valid is False
        assert any(error.code == "node_id_not_found" for error in result.errors)
