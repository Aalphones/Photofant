"""Qwen2.5-VL captioner adapter — instruct mode (§12.6).

Uses Qwen2_5VLForConditionalGeneration + AutoProcessor from transformers.
Loaded via GenerativeEngine to coordinate VRAM with other generative models.
Config contract: validated by caption_config._validate_instruct_config.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from photofant.inference.caption_config import (
    QWEN_DEFAULT_MAX_PIXELS,
    QWEN_DEFAULT_MIN_PIXELS,
    default_instruct_config,
)

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

_MANIFEST_ID = "qwen2-5-vl-7b"


class QwenVLCaptioner:
    """Captioner backed by Qwen2.5-VL (transformers, torch, heavy).

    The model is loaded via GenerativeEngine on first use and evicted after
    the idle timeout or when another generative model is requested.
    """

    def __init__(self, model_dir: str) -> None:
        self._model_dir = str(Path(model_dir))

    def caption(self, image: np.ndarray, preset: dict[str, Any]) -> str:  # type: ignore[type-arg]
        from PIL import Image as PILImage

        from photofant.inference.generative_engine import check_generative_available, generative_engine

        if check_generative_available().value != "available":
            log.warning("Generative dependencies not available — skipping Qwen2.5-VL caption")
            return ""

        config = preset or default_instruct_config()
        system_prompt: str = config.get("system_prompt", "")
        user_prompt: str = config.get("user_prompt", "Describe this image.")
        temperature: float = float(config.get("temperature", 0.7))
        top_p: float = float(config.get("top_p", 0.9))
        max_new_tokens: int = int(config.get("max_new_tokens", 512))
        repetition_penalty: float = float(config.get("repetition_penalty", 1.05))
        min_pixels: int = int(config.get("min_pixels", QWEN_DEFAULT_MIN_PIXELS))
        max_pixels: int = int(config.get("max_pixels", QWEN_DEFAULT_MAX_PIXELS))

        model, processor = generative_engine.load_transformers_model(
            model_id=_MANIFEST_ID,
            model_path=self._model_dir,
            model_class_name="Qwen2_5VLForConditionalGeneration",
        )

        pil_image = PILImage.fromarray(image)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image, "min_pixels": min_pixels, "max_pixels": max_pixels},
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]

        chat_template = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(
            text=[chat_template],
            images=[pil_image],
            return_tensors="pt",
        )

        import torch
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        generate_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "repetition_penalty": repetition_penalty,
        }
        if temperature > 0.0:
            generate_kwargs["do_sample"] = True
            generate_kwargs["temperature"] = temperature
            generate_kwargs["top_p"] = top_p
        else:
            generate_kwargs["do_sample"] = False

        with torch.no_grad():
            output_ids = model.generate(**inputs, **generate_kwargs)

        input_len = inputs["input_ids"].shape[1]
        generated_ids = output_ids[:, input_len:]
        text: str = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text.strip()


def resolve_qwen_captioner() -> QwenVLCaptioner | None:
    """Return a QwenVLCaptioner if the model is enabled in the registry; None otherwise."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=_MANIFEST_ID, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.debug("Qwen2.5-VL model not enabled or has no path — skipping")
            return None
        model_dir = entry.path

    return QwenVLCaptioner(model_dir=model_dir)
