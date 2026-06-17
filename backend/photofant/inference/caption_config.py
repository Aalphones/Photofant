"""Caption-mode constants, Florence task-prompt mapping, and preset validation.

This module owns the *contract* between a `caption_preset.config` JSON blob and
the captioner that consumes it. The pipeline and the CRUD endpoint validate
configs here; the Florence adapter reads the effective values via
`task_token_settings`.

Florence-2 does NOT consume the literal task token (e.g. ``<DETAILED_CAPTION>``).
The reference processor substitutes a natural-language prompt per task — we
replicate that mapping in `FLORENCE_TASK_PROMPTS`.
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
    on any violation. Only `task_token` is implemented today; `instruct` /
    `instruct_guided` arrive with their models (P6+) and are rejected for now.
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

    if caption_mode in (CaptionMode.INSTRUCT, CaptionMode.INSTRUCT_GUIDED):
        raise CaptionConfigError(
            "MODE_UNSUPPORTED",
            f"caption_mode {caption_mode!r} is not implemented yet (arrives with its model)",
        )

    raise CaptionConfigError("UNKNOWN_MODE", f"unknown caption_mode {caption_mode!r}")


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
