"""Florence-2 captioner adapter — implements the Captioner protocol on pure ONNX Runtime.

Florence-2 is an encoder-decoder vision-language model. Microsoft ships a torch
build; we run the onnx-community export (``onnx/*.onnx``) on onnxruntime and
implement prompt construction, the merged-decoder KV-cache generation loop, and
beam search ourselves. The HuggingFace ``tokenizers`` library is the ONLY extra
dependency and is used purely as a tokenizer — no torch in the core path
(Konzept §19.6).

Model directory layout (HF snapshot of onnx-community/Florence-2-base):
  <models_dir>/florence-2-base/
      onnx/embed_tokens.onnx
      onnx/vision_encoder.onnx
      onnx/encoder_model.onnx
      onnx/decoder_model_merged.onnx
      tokenizer.json
      generation_config.json   (optional — special-token ids)

Florence-2 does NOT consume the literal task token (e.g. ``<DETAILED_CAPTION>``).
The reference processor substitutes a natural-language prompt per task; that
mapping lives in `caption_config.FLORENCE_TASK_PROMPTS`.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from photofant.inference.caption_config import task_token_settings

if TYPE_CHECKING:
    import onnxruntime as ort

log = logging.getLogger(__name__)

_MANIFEST_ID = "florence-2-base"

# Bart-style defaults; overridden from generation_config.json when present.
_DEFAULT_DECODER_START_TOKEN = 2
_DEFAULT_EOS_TOKEN = 2


@lru_cache(maxsize=2)
def _load_tokenizer(tokenizer_path: str) -> Any:
    """Load a HuggingFace fast tokenizer from tokenizer.json (cached per path)."""
    from tokenizers import Tokenizer

    return Tokenizer.from_file(tokenizer_path)


def _log_softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable log-softmax over the last axis."""
    shifted = logits - logits.max(axis=-1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))


def _run(session: ort.InferenceSession, feeds: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Run a session, returning outputs keyed by their declared names."""
    output_names = [output.name for output in session.get_outputs()]
    results = session.run(output_names, feeds)
    return dict(zip(output_names, results, strict=True))


class Florence2Captioner:
    """Captioner backed by the onnx-community Florence-2 export.

    The four ONNX sessions are owned by `session_manager` (lazy load / idle
    eviction); the tokenizer is cached globally per file.
    """

    def __init__(self, model_dir: str) -> None:
        self._model_dir = Path(model_dir)
        onnx_dir = self._model_dir / "onnx"
        self._embed_path = str(onnx_dir / "embed_tokens.onnx")
        self._vision_path = str(onnx_dir / "vision_encoder.onnx")
        self._encoder_path = str(onnx_dir / "encoder_model.onnx")
        self._decoder_path = self._resolve_decoder_path(onnx_dir)
        self._tokenizer_path = str(self._model_dir / "tokenizer.json")
        self._decoder_start, self._eos_token = self._read_special_tokens()

    @staticmethod
    def _resolve_decoder_path(onnx_dir: Path) -> str:
        """Prefer the merged decoder (KV-cache branch); fall back to the plain one."""
        merged = onnx_dir / "decoder_model_merged.onnx"
        if merged.is_file():
            return str(merged)
        return str(onnx_dir / "decoder_model.onnx")

    def _read_special_tokens(self) -> tuple[int, int]:
        config_path = self._model_dir / "generation_config.json"
        if not config_path.is_file():
            return _DEFAULT_DECODER_START_TOKEN, _DEFAULT_EOS_TOKEN
        try:
            data: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("Could not read generation_config.json — using Bart defaults")
            return _DEFAULT_DECODER_START_TOKEN, _DEFAULT_EOS_TOKEN
        start = int(data.get("decoder_start_token_id", _DEFAULT_DECODER_START_TOKEN))
        eos = int(data.get("eos_token_id", _DEFAULT_EOS_TOKEN))
        return start, eos

    # ------------------------------------------------------------------
    # Captioner protocol
    # ------------------------------------------------------------------

    def caption(self, image: np.ndarray, preset: dict) -> str:  # type: ignore[type-arg]
        from photofant.inference.preprocessing import preprocess_for_florence
        from photofant.inference.session_manager import session_manager

        prompt, max_new_tokens, num_beams = task_token_settings(preset)
        tokenizer = _load_tokenizer(self._tokenizer_path)

        pixel_values = preprocess_for_florence(image)

        pool_size = 1  # TODO(P19 Phase 2): wire from load_settings()["captioning_workers"]
        embed_session = session_manager.acquire_exclusive_session(self._embed_path, pool_size)
        vision_session = session_manager.acquire_exclusive_session(self._vision_path, pool_size)
        encoder_session = session_manager.acquire_exclusive_session(self._encoder_path, pool_size)
        decoder_session = session_manager.acquire_exclusive_session(self._decoder_path, pool_size)
        try:
            encoder_hidden, encoder_mask = self._encode(
                embed_session, vision_session, encoder_session, tokenizer, prompt, pixel_values
            )
            token_ids = self._generate(
                embed_session,
                decoder_session,
                encoder_hidden,
                encoder_mask,
                num_beams=max(1, num_beams),
                max_new_tokens=max_new_tokens,
            )
        finally:
            session_manager.release_exclusive_session(self._embed_path, embed_session)
            session_manager.release_exclusive_session(self._vision_path, vision_session)
            session_manager.release_exclusive_session(self._encoder_path, encoder_session)
            session_manager.release_exclusive_session(self._decoder_path, decoder_session)

        text: str = tokenizer.decode(token_ids, skip_special_tokens=True)
        return text.strip()

    # ------------------------------------------------------------------
    # Encode: image features + task prompt → encoder hidden states
    # ------------------------------------------------------------------

    def _embed(self, embed_session: ort.InferenceSession, input_ids: np.ndarray) -> np.ndarray:
        input_name = embed_session.get_inputs()[0].name
        outputs = _run(embed_session, {input_name: input_ids.astype(np.int64)})
        return next(iter(outputs.values())).astype(np.float32)

    def _encode(
        self,
        embed_session: ort.InferenceSession,
        vision_session: ort.InferenceSession,
        encoder_session: ort.InferenceSession,
        tokenizer: Any,
        prompt: str,
        pixel_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        vision_input = vision_session.get_inputs()[0].name
        image_features = next(iter(_run(vision_session, {vision_input: pixel_values}).values())).astype(np.float32)

        prompt_ids = np.array([tokenizer.encode(prompt).ids], dtype=np.int64)  # (1, T) with <s>…</s>
        prompt_embeds = self._embed(embed_session, prompt_ids)  # (1, T, D)

        inputs_embeds = np.concatenate([image_features, prompt_embeds], axis=1)  # (1, N+T, D)
        attention_mask = np.ones((1, inputs_embeds.shape[1]), dtype=np.int64)

        encoder_outputs = _run(
            encoder_session,
            {"inputs_embeds": inputs_embeds, "attention_mask": attention_mask},
        )
        encoder_hidden = next(iter(encoder_outputs.values())).astype(np.float32)
        return encoder_hidden, attention_mask

    # ------------------------------------------------------------------
    # Decode: merged-decoder beam search (num_beams == 1 → greedy)
    # ------------------------------------------------------------------

    def _empty_past(self, decoder_session: ort.InferenceSession, batch: int) -> dict[str, np.ndarray]:
        """Zero-length KV cache for the first decode pass (use_cache_branch = False)."""
        past: dict[str, np.ndarray] = {}
        for model_input in decoder_session.get_inputs():
            if not model_input.name.startswith("past_key_values."):
                continue
            shape = model_input.shape  # [batch, num_heads, past_seq, head_dim]
            num_heads, head_dim = shape[1], shape[3]
            if not isinstance(num_heads, int) or not isinstance(head_dim, int):
                raise RuntimeError(
                    f"Florence-2 decoder input {model_input.name!r} has non-static head dims {shape!r}"
                )
            past[model_input.name] = np.zeros((batch, num_heads, 0, head_dim), dtype=np.float32)
        if not past:
            raise RuntimeError("Florence-2 decoder exposes no past_key_values inputs — expected the merged export")
        return past

    @staticmethod
    def _reorder_present(outputs: dict[str, np.ndarray], beam_order: np.ndarray) -> dict[str, np.ndarray]:
        """Map present.* → past_key_values.* and gather the rows for the surviving beams.

        The merged decoder emits zero-sized present tensors on the non-cache branch — skip them.
        """
        past: dict[str, np.ndarray] = {}
        for name, value in outputs.items():
            if name.startswith("present.") and value.shape[0] > 0:
                past_name = name.replace("present.", "past_key_values.", 1)
                past[past_name] = value[beam_order]
        return past

    def _generate(
        self,
        embed_session: ort.InferenceSession,
        decoder_session: ort.InferenceSession,
        encoder_hidden: np.ndarray,
        encoder_mask: np.ndarray,
        *,
        num_beams: int,
        max_new_tokens: int,
    ) -> list[int]:
        declared_inputs = {model_input.name for model_input in decoder_session.get_inputs()}
        encoder_hidden_beams = np.repeat(encoder_hidden, num_beams, axis=0)
        encoder_mask_beams = np.repeat(encoder_mask, num_beams, axis=0)

        # Encoder and decoder KV caches have different lifecycles:
        # - encoder KV (cross-attention): constant after step 0; zero-sized dummy until the model
        #   outputs real values (some exports never do — then we stay on non-cache branch forever)
        # - decoder KV (self-attention): grows by one token each step
        initial_past = self._empty_past(decoder_session, batch=num_beams)
        encoder_past: dict[str, np.ndarray] = {k: v for k, v in initial_past.items() if ".encoder." in k}
        decoder_past: dict[str, np.ndarray] = {k: v for k, v in initial_past.items() if ".decoder." in k}
        use_cache = False

        sequences: list[list[int]] = [[self._decoder_start] for _ in range(num_beams)]
        beam_scores = np.full((num_beams,), -1.0e9, dtype=np.float32)
        beam_scores[0] = 0.0
        next_input_ids = np.full((num_beams, 1), self._decoder_start, dtype=np.int64)

        finished: list[tuple[float, list[int]]] = []

        for _step in range(max_new_tokens):
            decoder_embeds = self._embed(embed_session, next_input_ids)
            feeds: dict[str, np.ndarray] = {
                "inputs_embeds": decoder_embeds,
                "encoder_hidden_states": encoder_hidden_beams,
                "encoder_attention_mask": encoder_mask_beams,
                "use_cache_branch": np.array([use_cache], dtype=bool),
            }
            feeds.update({**encoder_past, **decoder_past})
            feeds = {name: value for name, value in feeds.items() if name in declared_inputs}

            outputs = _run(decoder_session, feeds)
            next_logits = outputs["logits"][:, -1, :].astype(np.float32)  # (beams, vocab)
            log_probs = _log_softmax(next_logits)
            vocab_size = log_probs.shape[1]
            candidate_scores = (log_probs + beam_scores[:, None]).reshape(-1)  # (beams*vocab,)

            num_candidates = min(2 * num_beams, candidate_scores.shape[0])
            top_indices = np.argpartition(-candidate_scores, num_candidates - 1)[:num_candidates]
            top_indices = top_indices[np.argsort(-candidate_scores[top_indices])]

            next_beams: list[tuple[float, int, int]] = []  # (score, source_beam, token)
            for flat_index in top_indices:
                source_beam = int(flat_index // vocab_size)
                token = int(flat_index % vocab_size)
                score = float(candidate_scores[flat_index])
                if token == self._eos_token:
                    finished.append((score, sequences[source_beam] + [token]))
                else:
                    next_beams.append((score, source_beam, token))
                if len(next_beams) == num_beams:
                    break

            if not next_beams:
                break

            beam_scores = np.array([beam[0] for beam in next_beams], dtype=np.float32)
            beam_order = np.array([beam[1] for beam in next_beams], dtype=np.int64)
            sequences = [sequences[beam[1]] + [beam[2]] for beam in next_beams]
            next_input_ids = np.array([beam[2] for beam in next_beams], dtype=np.int64)[:, None]

            new_past = self._reorder_present(outputs, beam_order)
            new_encoder = {k: v for k, v in new_past.items() if ".encoder." in k}
            new_decoder = {k: v for k, v in new_past.items() if ".decoder." in k}

            if new_encoder:
                # Model produced real encoder KV (cross-attention cache) — keep them.
                # After step 0 these never change, so we don't need to update them again;
                # but if the model re-emits them on cache steps, accept the update anyway.
                encoder_past = new_encoder
            else:
                # Model did not output encoder KV (common in some merged-decoder exports).
                # Reorder the existing dummy tensors so batch indices stay aligned with beams.
                encoder_past = {k: v[beam_order] for k, v in encoder_past.items()}

            if new_decoder:
                decoder_past = new_decoder

            # Cache branch requires real (non-zero-length) encoder KV; stay on non-cache branch
            # if only zero-sized dummies are available.
            encoder_seq_len = next(iter(encoder_past.values())).shape[2] if encoder_past else 0
            use_cache = encoder_seq_len > 0 and bool(decoder_past)

            if len(finished) >= num_beams and max(score for score, _ in finished) >= beam_scores.max():
                break

        if not finished:
            finished = [(float(beam_scores[index]), sequences[index]) for index in range(len(sequences))]
        candidates = finished
        # Length-normalized score (length penalty α = 1) — favours complete, fluent captions.
        best_score, best_sequence = max(candidates, key=lambda item: item[0] / max(len(item[1]) - 1, 1))
        log.debug("Florence-2: best beam score %.3f, %d tokens", best_score, len(best_sequence))
        return best_sequence[1:]  # drop the decoder-start token


def resolve_florence_captioner() -> Florence2Captioner | None:
    """Return a Florence2Captioner if the model is enabled in the registry; None otherwise."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=_MANIFEST_ID, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.info("Florence-2 model not enabled or has no path — skipping")
            return None
        model_dir = entry.path

    return Florence2Captioner(model_dir=model_dir)
