"""Caption-mode constants and preset validation for all supported captioners.

Owns the *contract* between a `caption_preset.config` JSON blob and the captioner
that consumes it. Three modes (§12.6):

- ``task_token`` — Florence-2: fixed task tokens, deterministic beam search.
- ``instruct`` — Qwen2.5-VL: free system/user prompt + sampling parameters.
- ``instruct_guided`` — JoyCaption: structured prompt built from typed blocks.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any


class CaptionMode(StrEnum):
    """How a captioner is steered — mirrors `model_registry.caption_mode` (§12.6)."""

    TASK_TOKEN = "task_token"
    INSTRUCT = "instruct"
    INSTRUCT_GUIDED = "instruct_guided"


# Florence-2 task token → natural-language prompt the model was trained on.
# Source: microsoft/Florence-2 `Florence2Processor` task_prompts_without_inputs.
FLORENCE_TASK_PROMPTS: dict[str, str] = {
    "<CAPTION>": "What does the image describe?",
    "<DETAILED_CAPTION>": "Describe in detail what is shown in the image.",
    "<MORE_DETAILED_CAPTION>": "Describe with a paragraph what is shown in the image.",
}

CAPTION_TASK_TOKENS: tuple[str, ...] = tuple(FLORENCE_TASK_PROMPTS)

DEFAULT_TASK_TOKEN = "<DETAILED_CAPTION>"
DEFAULT_MAX_NEW_TOKENS = 1024
DEFAULT_NUM_BEAMS = 3

_MAX_NEW_TOKENS_LIMIT = 4096
_NUM_BEAMS_LIMIT = 16

# ---------------------------------------------------------------------------
# Qwen2.5-VL (instruct) defaults
# ---------------------------------------------------------------------------

QWEN_DEFAULT_SYSTEM_PROMPT_NATURAL = (
    "You are a helpful vision assistant. Describe the image in natural, fluent prose. "
    "Focus on the main subject, composition, colors, and mood."
)
QWEN_DEFAULT_USER_PROMPT = "Describe this image."
QWEN_DEFAULT_TEMPERATURE = 0.7
QWEN_DEFAULT_TOP_P = 0.9
QWEN_DEFAULT_MAX_NEW_TOKENS = 512
QWEN_DEFAULT_REPETITION_PENALTY = 1.05
QWEN_DEFAULT_MIN_PIXELS = 256 * 28 * 28   # 200704
QWEN_DEFAULT_MAX_PIXELS = 1280 * 28 * 28  # 1003520

# ---------------------------------------------------------------------------
# JoyCaption (instruct_guided) defaults
# ---------------------------------------------------------------------------

JOYCAPTION_CAPTION_TYPES: tuple[str, ...] = (
    "Descriptive",
    "Straightforward",
    "Stable Diffusion Prompt",
    "Booru Tag List",
    "Art Critic",
    "Product Listing",
    "Social Media Post",
)
JOYCAPTION_CAPTION_LENGTHS: tuple[str, ...] = (
    "any",
    "very short",
    "short",
    "medium",
    "long",
    "very long",
)
JOYCAPTION_DEFAULT_CAPTION_TYPE = "Descriptive"
JOYCAPTION_DEFAULT_CAPTION_LENGTH = "medium"


class CaptionConfigError(ValueError):
    """A caption_preset.config blob is invalid for its caption_mode."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def default_task_token_config() -> dict[str, Any]:
    """The built-in task_token config used when no preset is supplied."""
    return {
        "task_token": DEFAULT_TASK_TOKEN,
        "max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
        "num_beams": DEFAULT_NUM_BEAMS,
    }


def _require_int(config: dict[str, Any], key: str, default: int, upper: int) -> int:
    raw = config.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise CaptionConfigError("INVALID_FIELD", f"{key!r} must be an integer")
    if raw < 1 or raw > upper:
        raise CaptionConfigError("OUT_OF_RANGE", f"{key!r} must be between 1 and {upper}")
    return raw


def validate_caption_config(caption_mode: str, config: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a preset config against its caption_mode.

    Returns the normalized config (defaults filled in). Raises CaptionConfigError
    on any violation.
    """
    if caption_mode == CaptionMode.TASK_TOKEN:
        task_token = config.get("task_token", DEFAULT_TASK_TOKEN)
        if task_token not in CAPTION_TASK_TOKENS:
            raise CaptionConfigError(
                "UNKNOWN_TASK_TOKEN",
                f"task_token must be one of {', '.join(CAPTION_TASK_TOKENS)}",
            )
        return {
            "task_token": task_token,
            "max_new_tokens": _require_int(config, "max_new_tokens", DEFAULT_MAX_NEW_TOKENS, _MAX_NEW_TOKENS_LIMIT),
            "num_beams": _require_int(config, "num_beams", DEFAULT_NUM_BEAMS, _NUM_BEAMS_LIMIT),
        }

    if caption_mode == CaptionMode.INSTRUCT:
        return _validate_instruct_config(config)

    if caption_mode == CaptionMode.INSTRUCT_GUIDED:
        return _validate_instruct_guided_config(config)

    raise CaptionConfigError("UNKNOWN_MODE", f"unknown caption_mode {caption_mode!r}")


def _require_float(config: dict[str, Any], key: str, default: float, lo: float, hi: float) -> float:
    raw = config.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise CaptionConfigError("INVALID_FIELD", f"{key!r} must be a number")
    value = float(raw)
    if value < lo or value > hi:
        raise CaptionConfigError("OUT_OF_RANGE", f"{key!r} must be between {lo} and {hi}")
    return value


def _validate_instruct_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a Qwen2.5-VL (instruct) preset config."""
    system_prompt = config.get("system_prompt", QWEN_DEFAULT_SYSTEM_PROMPT_NATURAL)
    if not isinstance(system_prompt, str):
        raise CaptionConfigError("INVALID_FIELD", "'system_prompt' must be a string")

    user_prompt = config.get("user_prompt", QWEN_DEFAULT_USER_PROMPT)
    if not isinstance(user_prompt, str):
        raise CaptionConfigError("INVALID_FIELD", "'user_prompt' must be a string")

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "temperature": _require_float(config, "temperature", QWEN_DEFAULT_TEMPERATURE, 0.0, 1.5),
        "top_p": _require_float(config, "top_p", QWEN_DEFAULT_TOP_P, 0.0, 1.0),
        "max_new_tokens": _require_int(config, "max_new_tokens", QWEN_DEFAULT_MAX_NEW_TOKENS, _MAX_NEW_TOKENS_LIMIT),
        "repetition_penalty": _require_float(config, "repetition_penalty", QWEN_DEFAULT_REPETITION_PENALTY, 1.0, 2.0),
        "min_pixels": _require_int(config, "min_pixels", QWEN_DEFAULT_MIN_PIXELS, 2**31 - 1),
        "max_pixels": _require_int(config, "max_pixels", QWEN_DEFAULT_MAX_PIXELS, 2**31 - 1),
    }


def _validate_instruct_guided_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a JoyCaption (instruct_guided) preset config."""
    caption_type = config.get("caption_type", JOYCAPTION_DEFAULT_CAPTION_TYPE)
    if caption_type not in JOYCAPTION_CAPTION_TYPES:
        raise CaptionConfigError(
            "UNKNOWN_CAPTION_TYPE",
            f"caption_type must be one of: {', '.join(JOYCAPTION_CAPTION_TYPES)}",
        )

    caption_length = config.get("caption_length", JOYCAPTION_DEFAULT_CAPTION_LENGTH)
    if caption_length not in JOYCAPTION_CAPTION_LENGTHS:
        raise CaptionConfigError(
            "UNKNOWN_CAPTION_LENGTH",
            f"caption_length must be one of: {', '.join(JOYCAPTION_CAPTION_LENGTHS)}",
        )

    extra_options = config.get("extra_options", [])
    if not isinstance(extra_options, list) or not all(isinstance(item, str) for item in extra_options):
        raise CaptionConfigError("INVALID_FIELD", "'extra_options' must be a list of strings")

    person_name = config.get("person_name", "")
    if not isinstance(person_name, str):
        raise CaptionConfigError("INVALID_FIELD", "'person_name' must be a string")

    raw_prompt_override = config.get("raw_prompt_override", "")
    if not isinstance(raw_prompt_override, str):
        raise CaptionConfigError("INVALID_FIELD", "'raw_prompt_override' must be a string")

    return {
        "caption_type": caption_type,
        "caption_length": caption_length,
        "extra_options": extra_options,
        "person_name": person_name,
        "raw_prompt_override": raw_prompt_override,
    }


def default_instruct_config(system_prompt: str | None = None) -> dict[str, Any]:
    """Built-in instruct defaults used when no Qwen preset is configured."""
    return {
        "system_prompt": system_prompt or QWEN_DEFAULT_SYSTEM_PROMPT_NATURAL,
        "user_prompt": QWEN_DEFAULT_USER_PROMPT,
        "temperature": QWEN_DEFAULT_TEMPERATURE,
        "top_p": QWEN_DEFAULT_TOP_P,
        "max_new_tokens": QWEN_DEFAULT_MAX_NEW_TOKENS,
        "repetition_penalty": QWEN_DEFAULT_REPETITION_PENALTY,
        "min_pixels": QWEN_DEFAULT_MIN_PIXELS,
        "max_pixels": QWEN_DEFAULT_MAX_PIXELS,
    }


def default_instruct_guided_config() -> dict[str, Any]:
    """Built-in instruct_guided defaults used when no JoyCaption preset is configured."""
    return {
        "caption_type": JOYCAPTION_DEFAULT_CAPTION_TYPE,
        "caption_length": JOYCAPTION_DEFAULT_CAPTION_LENGTH,
        "extra_options": [],
        "person_name": "",
        "raw_prompt_override": "",
    }


def task_token_settings(preset_config: dict[str, Any] | None) -> tuple[str, int, int]:
    """Extract (prompt, max_new_tokens, num_beams) for a Florence run from a preset.

    Falls back to the built-in defaults for any missing key; maps the task token
    to the prompt string Florence actually expects.
    """
    config = preset_config or default_task_token_config()
    task_token = config.get("task_token", DEFAULT_TASK_TOKEN)
    prompt = FLORENCE_TASK_PROMPTS.get(task_token, FLORENCE_TASK_PROMPTS[DEFAULT_TASK_TOKEN])
    max_new_tokens = int(config.get("max_new_tokens", DEFAULT_MAX_NEW_TOKENS))
    num_beams = int(config.get("num_beams", DEFAULT_NUM_BEAMS))
    return prompt, max_new_tokens, num_beams
