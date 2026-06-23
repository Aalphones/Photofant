"""JoyCaption captioner adapter — instruct_guided mode (§12.6).

Uses LlavaForConditionalGeneration + AutoProcessor from transformers.
The system prompt is built from typed blocks (caption_type + length + extra_options);
a raw_prompt_override replaces the generated prompt for power users.
Config contract: validated by caption_config._validate_instruct_guided_config.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from photofant.inference.caption_config import default_instruct_guided_config

log = logging.getLogger(__name__)

_MANIFEST_ID = "joycaption-alpha-two"

# Maps caption_type → system-prompt instruction (§12.6 table).
_CAPTION_TYPE_PROMPTS: dict[str, str] = {
    "Descriptive": "Write a descriptive caption for this image in a formal tone.",
    "Straightforward": "Write a straightforward caption for this image.",
    "Stable Diffusion Prompt": "Write a stable diffusion prompt for this image.",
    "Booru Tag List": "Write a list of Booru tags for this image.",
    "Art Critic": "Analyze this image like an art critic would with a focus on the composition, style, and technique.",
    "Product Listing": "Write a caption for this image as though it were a product listing.",
    "Social Media Post": "Write a caption for this image as though it were a social media post.",
}

_LENGTH_SUFFIXES: dict[str, str] = {
    "any": "",
    "very short": " Keep it under 20 words.",
    "short": " Keep it under 50 words.",
    "medium": " Keep it between 50 and 100 words.",
    "long": " Keep it between 100 and 200 words.",
    "very long": " Keep it over 200 words.",
}

_SYSTEM_PROMPT = "You are a helpful image captioner."


def _build_user_prompt(config: dict[str, Any]) -> str:
    """Construct the user-facing instruction from instruct_guided config blocks."""
    raw_override: str = config.get("raw_prompt_override", "")
    if raw_override.strip():
        return raw_override.strip()

    caption_type: str = config.get("caption_type", "Descriptive")
    caption_length: str = config.get("caption_length", "medium")
    extra_options: list[str] = config.get("extra_options", [])
    person_name: str = config.get("person_name", "")

    base = _CAPTION_TYPE_PROMPTS.get(caption_type, _CAPTION_TYPE_PROMPTS["Descriptive"])
    length_suffix = _LENGTH_SUFFIXES.get(caption_length, "")
    prompt = base + length_suffix

    if extra_options:
        prompt += " Also include: " + "; ".join(extra_options) + "."

    if person_name.strip():
        prompt += f" The person in the image is named {person_name.strip()}."

    return prompt


class JoyCaptioner:
    """Captioner backed by JoyCaption alpha two (transformers, torch, heavy).

    The model is a LLaVA-style VLM loaded via GenerativeEngine. The guided
    prompt is constructed from the caption_type, length, extra_options, and
    optional person_name; a raw_prompt_override replaces it entirely.
    """

    def __init__(self, model_dir: str) -> None:
        self._model_dir = str(Path(model_dir))

    def caption(self, image: np.ndarray, preset: dict[str, Any]) -> str:  # type: ignore[type-arg]
        from PIL import Image as PILImage

        from photofant.inference.generative_engine import check_generative_available, generative_engine

        if check_generative_available().value != "available":
            log.warning("Generative dependencies not available — skipping JoyCaption")
            return ""

        config = preset or default_instruct_guided_config()
        user_prompt = _build_user_prompt(config)

        model, processor = generative_engine.load_transformers_model(
            model_id=_MANIFEST_ID,
            model_path=self._model_dir,
            model_class_name="LlavaForConditionalGeneration",
        )

        pil_image = PILImage.fromarray(image)

        # LLaVA conversation format: <image> placeholder in user turn.
        conversation = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image"},
                ],
            },
        ]

        prompt_text: str = processor.apply_chat_template(conversation, add_generation_prompt=True)
        inputs = processor(images=pil_image, text=prompt_text, return_tensors="pt")

        import torch
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
            )

        input_len = inputs["input_ids"].shape[1]
        generated_ids = output_ids[:, input_len:]
        text: str = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text.strip()


def resolve_joycaption() -> JoyCaptioner | None:
    """Return a JoyCaptioner if the model is enabled in the registry; None otherwise."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=_MANIFEST_ID, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.debug("JoyCaption model not enabled or has no path — skipping")
            return None
        model_dir = entry.path

    return JoyCaptioner(model_dir=model_dir)
