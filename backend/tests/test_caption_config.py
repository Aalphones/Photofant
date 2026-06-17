"""Caption-preset config validation + Florence task-prompt mapping (model-free)."""
from __future__ import annotations

import numpy as np
import pytest

from photofant.inference.caption_config import (
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_NUM_BEAMS,
    FLORENCE_TASK_PROMPTS,
    CaptionConfigError,
    CaptionMode,
    task_token_settings,
    validate_caption_config,
)
from photofant.inference.preprocessing import preprocess_for_florence


def test_task_token_maps_to_natural_language_prompt() -> None:
    prompt, max_new_tokens, num_beams = task_token_settings(
        {"task_token": "<MORE_DETAILED_CAPTION>", "max_new_tokens": 512, "num_beams": 5}
    )
    assert prompt == FLORENCE_TASK_PROMPTS["<MORE_DETAILED_CAPTION>"]
    assert max_new_tokens == 512
    assert num_beams == 5


def test_task_token_settings_fills_defaults_for_none() -> None:
    prompt, max_new_tokens, num_beams = task_token_settings(None)
    assert prompt == FLORENCE_TASK_PROMPTS["<DETAILED_CAPTION>"]
    assert max_new_tokens == DEFAULT_MAX_NEW_TOKENS
    assert num_beams == DEFAULT_NUM_BEAMS


def test_validate_task_token_normalizes_and_fills_defaults() -> None:
    normalized = validate_caption_config(CaptionMode.TASK_TOKEN, {"task_token": "<CAPTION>"})
    assert normalized == {
        "task_token": "<CAPTION>",
        "max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
        "num_beams": DEFAULT_NUM_BEAMS,
    }


def test_validate_rejects_unknown_task_token() -> None:
    with pytest.raises(CaptionConfigError) as raised:
        validate_caption_config(CaptionMode.TASK_TOKEN, {"task_token": "<ROAST_ME>"})
    assert raised.value.code == "UNKNOWN_TASK_TOKEN"


def test_validate_rejects_out_of_range_num_beams() -> None:
    with pytest.raises(CaptionConfigError) as raised:
        validate_caption_config(CaptionMode.TASK_TOKEN, {"task_token": "<CAPTION>", "num_beams": 99})
    assert raised.value.code == "OUT_OF_RANGE"


def test_validate_rejects_bool_passed_as_int() -> None:
    with pytest.raises(CaptionConfigError) as raised:
        validate_caption_config(CaptionMode.TASK_TOKEN, {"task_token": "<CAPTION>", "max_new_tokens": True})
    assert raised.value.code == "INVALID_FIELD"


def test_validate_rejects_unimplemented_instruct_mode() -> None:
    with pytest.raises(CaptionConfigError) as raised:
        validate_caption_config(CaptionMode.INSTRUCT, {"system_prompt": "describe"})
    assert raised.value.code == "MODE_UNSUPPORTED"


def test_florence_preprocessing_produces_768_nchw() -> None:
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    result = preprocess_for_florence(image)
    assert result.shape == (1, 3, 768, 768)
    assert result.dtype == np.float32
