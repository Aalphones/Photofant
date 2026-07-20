"""Format routing (ADR-029) + Vision-Naht — Registry/Settings gemockt, kein echtes Modell-Laden.

`resolve_generator` muss allein am Manifest-`format` zwischen dem torch- und dem
GGUF-Adapter routen (P35 Phase 2); die Vision-Naht muss strukturell (`isinstance`)
nur greifen, wenn ein `mmproj` gebunden ist (P35 Phase 1, ADR-029).
"""
from __future__ import annotations

from types import SimpleNamespace

from photofant.inference import capabilities
from photofant.inference.adapters.gemma import GemmaAdapter
from photofant.inference.adapters.gemma_gguf import GemmaGgufAdapter, GemmaGgufVisionAdapter
from photofant.inference.interfaces import TextGenerator, VisionTextGenerator


def _fake_settings(manifest_id: str) -> dict:
    return {"ai": {"gemmaModel": manifest_id, "capabilityMap": {}, "autonomy": {}}}


def test_resolve_generator_routes_safetensors_to_torch_adapter(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "load_settings", lambda: _fake_settings("gemma-3-4b-it"))
    monkeypatch.setattr(
        capabilities, "get_manifest_entry", lambda manifest_id: SimpleNamespace(format="safetensors")
    )
    sentinel = GemmaAdapter(manifest_id="gemma-3-4b-it", model_dir="/fake/path")
    monkeypatch.setattr(capabilities, "resolve_gemma", lambda manifest_id: sentinel)

    generator = capabilities.resolve_generator(capabilities.Capability.TEXT_GENERATION)

    assert generator is sentinel


def test_resolve_generator_routes_gguf_to_llama_cpp_adapter(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "load_settings", lambda: _fake_settings("gemma-4-12b-oblit-gguf"))
    monkeypatch.setattr(capabilities, "get_manifest_entry", lambda manifest_id: SimpleNamespace(format="gguf"))
    sentinel = GemmaGgufAdapter(manifest_id="gemma-4-12b-oblit-gguf", model_path="/fake/model.gguf")
    monkeypatch.setattr(capabilities, "resolve_gemma_gguf", lambda manifest_id: sentinel)

    generator = capabilities.resolve_generator(capabilities.Capability.TEXT_GENERATION)

    assert generator is sentinel


def test_resolve_generator_returns_none_when_manifest_entry_missing(monkeypatch) -> None:
    monkeypatch.setattr(capabilities, "load_settings", lambda: _fake_settings("unknown-model"))
    monkeypatch.setattr(capabilities, "get_manifest_entry", lambda manifest_id: None)

    generator = capabilities.resolve_generator(capabilities.Capability.TEXT_GENERATION)

    assert generator is None


def test_gemma_gguf_adapter_without_mmproj_is_not_a_vision_generator() -> None:
    adapter = GemmaGgufAdapter(manifest_id="gemma-gguf", model_path="/fake/model.gguf")

    assert isinstance(adapter, TextGenerator)
    assert not isinstance(adapter, VisionTextGenerator)


def test_gemma_gguf_vision_adapter_with_mmproj_satisfies_vision_generator() -> None:
    adapter = GemmaGgufVisionAdapter(
        manifest_id="gemma-gguf", model_path="/fake/model.gguf", mmproj_path="/fake/mmproj.gguf"
    )

    assert isinstance(adapter, VisionTextGenerator)
