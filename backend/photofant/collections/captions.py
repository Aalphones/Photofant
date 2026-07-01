"""Caption bulk-action logic for training sets (P10 Phase 3, Konzept §9).

Pure, side-effect-free transform shared by the apply job and the frontend's instant
preview (mirrored in TypeScript — no network round-trip needed for a 5-sample preview).
Operates on the *effective* base caption (override if set, else the gallery's original
caption) and returns the new caption_override value.

Trigger-word/prefix/suffix are idempotent: reapplying the same action never stacks the
same fragment twice (Phase-3 AK "Trigger-Word nicht doppelt voranstellen", generalized to
all three so repeated tool use never corrupts a caption). Find-Replace is naturally
idempotent via `str.replace` semantics.
"""
from __future__ import annotations

from typing import Any, Literal

CaptionAction = Literal["trigger_word", "prefix", "suffix", "find_replace"]
CAPTION_ACTIONS: tuple[CaptionAction, ...] = ("trigger_word", "prefix", "suffix", "find_replace")


def apply_caption_action(base: str | None, action: CaptionAction, params: dict[str, Any]) -> str:
    text = base or ""
    if action == "trigger_word":
        word = str(params.get("word") or "").strip()
        if not word:
            return text
        if text == word or text.startswith(f"{word}, "):
            return text
        return f"{word}, {text}" if text else word
    if action == "prefix":
        prefix = str(params.get("text") or "").strip()
        if not prefix:
            return text
        if text.startswith(prefix):
            return text
        return f"{prefix} {text}" if text else prefix
    if action == "suffix":
        suffix = str(params.get("text") or "").strip()
        if not suffix:
            return text
        if text.endswith(suffix):
            return text
        return f"{text} {suffix}" if text else suffix
    if action == "find_replace":
        find = str(params.get("find") or "")
        if not find:
            return text
        replace = str(params.get("replace") or "")
        return text.replace(find, replace)
    raise ValueError(f"unknown caption action: {action}")
