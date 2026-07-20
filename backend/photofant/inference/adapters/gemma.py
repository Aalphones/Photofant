"""Gemma text-generation adapter — torch/transformers, lazy-load (ADR-028).

Gemma is a plain causal LM (text in, text out). It rides the **existing**
generative model lifecycle (`GenerativeEngine`): lazy-loaded on first use,
one model resident at a time, idle-unloaded by the app's eviction loop, offline
env enforced. No new load path — the only difference to the JoyCaption/Qwen-VL
captioners is that a text LM has no `AutoProcessor`; it loads a tokenizer instead
(`load_processor=False`).

Gemma's chat template has no `system` role — a system instruction is folded into
the user turn.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


class GemmaAdapter:
    """`TextGenerator` backed by a Gemma instruct model via transformers."""

    def __init__(self, manifest_id: str, model_dir: str) -> None:
        self._manifest_id = manifest_id
        self._model_dir = str(Path(model_dir))

    @property
    def model_id(self) -> str:
        return self._manifest_id

    def generate(self, prompt: str, *, system: str | None = None, max_new_tokens: int = 512) -> str:
        from photofant.inference.generative_engine import check_generative_available, generative_engine

        if check_generative_available().value != "available":
            log.warning("Generative dependencies not available — skipping Gemma generation")
            return ""

        model, tokenizer = generative_engine.load_transformers_model(
            model_id=self._manifest_id,
            model_path=self._model_dir,
            model_class_name="AutoModelForCausalLM",
            load_processor=False,
        )

        # Gemma's chat template rejects a "system" role — fold the instruction
        # into the user turn instead of relying on template support.
        user_text = prompt if not system else f"{system}\n\n{prompt}"
        messages = [{"role": "user", "content": user_text}]

        input_ids = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt"
        )

        import torch

        device = next(model.parameters()).device
        input_ids = input_ids.to(device)

        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )

        prompt_len: int = input_ids.shape[1]
        generated_ids = output_ids[0, prompt_len:]
        text: str = tokenizer.decode(generated_ids, skip_special_tokens=True)
        return text.strip()


def resolve_gemma(manifest_id: str) -> GemmaAdapter | None:
    """Return a GemmaAdapter if *manifest_id* is enabled in the registry; None otherwise.

    Mirrors `resolve_joycaption`: the DB registry maps a manifest_id to the
    on-disk model path; a disabled or unbound model degrades gracefully to None.
    """
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=manifest_id, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.debug("Gemma model %r not enabled or has no path — skipping", manifest_id)
            return None
        model_dir = entry.path

    return GemmaAdapter(manifest_id=manifest_id, model_dir=model_dir)
