"""Capability registry — jobs ask for a *capability*, never a model (ADR-027).

A job that needs text generation requests `Capability.TEXT_GENERATION`; the
registry resolves it to a concrete model via the `ai.capabilityMap` setting
(capability → manifest_id, defaulting to `ai.gemmaModel`) and returns a
`TextGenerator`. Swapping the model behind a capability is a settings change,
not a code change — no job ever names Gemma.

Every generation returns a `GenerationResult` carrying the explainability payload
(model, capability, prompt version, duration, confidence — Dok 040 §12).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from photofant.inference.adapters.gemma import resolve_gemma
from photofant.inference.interfaces import TextGenerator
from photofant.settings import load_settings


class Capability(StrEnum):
    """A skill a job needs. Mapped to a model by `ai.capabilityMap`, not hard-wired."""

    TEXT_GENERATION = "text_generation"
    KNOWLEDGE_IMPORT = "knowledge_import"
    KNOWLEDGE_UPDATE = "knowledge_update"
    INTERVIEW = "interview"


class CapabilityUnavailableError(RuntimeError):
    """The model mapped to a capability is not enabled/bound in the registry."""


@dataclass
class GenerationResult:
    """Text plus the explainability payload every AI call must carry (Dok 040 §12).

    `prompt_version` is threaded through from the prompt library by the caller;
    `confidence` is populated by capabilities that can derive one (the free-text
    demo path leaves it None — a raw LM emits no calibrated confidence).
    """

    text: str
    model_id: str
    capability: str
    prompt_version: str | None
    duration_ms: float
    confidence: float | None = None


# Which autonomy setting gates each capability. TEXT_GENERATION is the raw engine
# with no user-facing on/off of its own.
_AUTONOMY_KEY: dict[Capability, str] = {
    Capability.KNOWLEDGE_IMPORT: "knowledge_import",
    Capability.KNOWLEDGE_UPDATE: "knowledge_update",
    Capability.INTERVIEW: "interview",
}


def resolve_generator(capability: Capability) -> TextGenerator | None:
    """Return the `TextGenerator` mapped to *capability*, or None if not enabled."""
    ai = load_settings()["ai"]
    manifest_id = ai["capabilityMap"].get(capability.value) or ai["gemmaModel"]
    return resolve_gemma(manifest_id)


def autonomy_for(capability: Capability) -> str:
    """Return the autonomy mode (`off` | `ask` | `auto`) configured for *capability*.

    Later phases gate on this: `off` means the KI action is not offered and the
    manual MVP path (P22–P25) stands in. TEXT_GENERATION has no gate → `auto`.
    """
    key = _AUTONOMY_KEY.get(capability)
    if key is None:
        return "auto"
    ai = load_settings()["ai"]
    return ai["autonomy"].get(key, "ask")


def generate(
    capability: Capability,
    prompt: str,
    *,
    system: str | None = None,
    max_new_tokens: int = 512,
    prompt_version: str | None = None,
) -> GenerationResult:
    """Run text generation for *capability* and wrap it in the explainability payload.

    Raises `CapabilityUnavailableError` when no model is bound to the capability —
    callers decide whether that degrades to the manual path or surfaces an error.
    """
    generator = resolve_generator(capability)
    if generator is None:
        raise CapabilityUnavailableError(
            f"Kein Modell für Fähigkeit '{capability.value}' aktiviert"
        )

    start = time.monotonic()
    text = generator.generate(prompt, system=system, max_new_tokens=max_new_tokens)
    duration_ms = (time.monotonic() - start) * 1000.0

    return GenerationResult(
        text=text,
        model_id=generator.model_id,
        capability=capability.value,
        prompt_version=prompt_version,
        duration_ms=duration_ms,
    )
