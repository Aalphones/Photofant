# Phase 3 — Docs + Test

**Komplexität:** mechanisch · **Status:** pending

## Kontext (lesen, bevor du baust)
- [docs/decisions/028-gemma-runtime.md](../../../docs/decisions/028-gemma-runtime.md) — bekommt einen Nachtrag (GGUF-Adapter existiert jetzt, ADR-028 bleibt gültig für den torch-Pfad).
- [docs/code-map.md](../../../docs/code-map.md) — Feature-Zeilen-Schema.
- [docs/models.md](../../../docs/models.md) — Manifest-Doku.
- Test-Vorbild: `backend/tests/` (ein bestehender Adapter-/Resolver-Test als Muster).

## AK der Phase
- [ ] ADR-029 dokumentiert die VRAM-Koordination (Kontext / Optionen: Cross-Unload vs. Arbiter / Entscheidung / Konsequenzen).
- [ ] ADR-028 hat einen kurzen Nachtrag: „GGUF-Adapter als zweite Runtime umgesetzt (P35, ADR-029) — torch bleibt der Default-Pfad, keine Entscheidung revidiert."
- [ ] `code-map.md` + `models.md` nennen den GGUF-Adapter / -Manifest-Eintrag.
- [ ] ADR-029 / code-map halten die **Vision-Naht** fest: `VisionTextGenerator` definiert, mmproj optional ladbar, aber kein Konsument — der spätere Vision-Job braucht keinen Runtime-Umbau.
- [ ] Ein Test deckt die Format-Weiche ab: `resolve_generator` gibt bei `format=gguf` den GGUF-Adapter, bei `safetensors` den torch-Adapter (Registry gemockt, ohne echtes Modell zu laden).
- [ ] Ein Test deckt die Vision-Naht ab: ein `GemmaGgufAdapter` mit gebundenem mmproj erfüllt `isinstance(adapter, VisionTextGenerator)`, ohne mmproj nicht (Registry/Engine gemockt, kein echtes Laden).

## Checkliste
- [ ] `docs/decisions/029-gemma-gguf-vram-koordination.md` neu.
- [ ] ADR-028 Nachtrag-Zeile.
- [ ] `code-map.md`: Zeile für `inference/gguf_engine.py` + `adapters/gemma_gguf.py`.
- [ ] `models.md`: GGUF-Manifest-Eintrag + `format: gguf`-Semantik + optionale mmproj-Datei.
- [ ] `backend/tests/test_capability_format_routing.py` (o.ä.): Format-Weiche + Vision-Naht (`isinstance`), Registry/Engine gemockt.
- [ ] `cd backend && uv run ruff check . && uv run pytest backend/tests/test_capability_format_routing.py` grün.
- [ ] STATE.md auf diesen Plan / Abschluss zeigen lassen.

## Report-Back
