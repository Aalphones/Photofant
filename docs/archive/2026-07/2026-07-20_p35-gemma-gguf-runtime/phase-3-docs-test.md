# Phase 3 — Docs + Test

**Komplexität:** mechanisch · **Status:** complete

## Kontext (lesen, bevor du baust)
- [docs/decisions/028-gemma-runtime.md](../../../docs/decisions/028-gemma-runtime.md) — bekommt einen Nachtrag (GGUF-Adapter existiert jetzt, ADR-028 bleibt gültig für den torch-Pfad).
- [docs/code-map.md](../../../docs/code-map.md) — Feature-Zeilen-Schema.
- [docs/models.md](../../../docs/models.md) — Manifest-Doku.
- Test-Vorbild: `backend/tests/` (ein bestehender Adapter-/Resolver-Test als Muster).

## AK der Phase
- [x] ADR-029 dokumentiert die VRAM-Koordination (Kontext / Optionen: Cross-Unload vs. Arbiter / Entscheidung / Konsequenzen). *(bereits in Phase 1 angelegt.)*
- [x] ADR-028 hat einen kurzen Nachtrag: „GGUF-Adapter als zweite Runtime umgesetzt (P35, ADR-029) — torch bleibt der Default-Pfad, keine Entscheidung revidiert."
- [x] `code-map.md` + `models.md` nennen den GGUF-Adapter / -Manifest-Eintrag.
- [x] ADR-029 / code-map halten die **Vision-Naht** fest: `VisionTextGenerator` definiert, mmproj optional ladbar, aber kein Konsument — der spätere Vision-Job braucht keinen Runtime-Umbau.
- [x] Ein Test deckt die Format-Weiche ab: `resolve_generator` gibt bei `format=gguf` den GGUF-Adapter, bei `safetensors` den torch-Adapter (Registry gemockt, ohne echtes Modell zu laden).
- [x] Ein Test deckt die Vision-Naht ab: ein `GemmaGgufAdapter` mit gebundenem mmproj erfüllt `isinstance(adapter, VisionTextGenerator)`, ohne mmproj nicht (Registry/Engine gemockt, kein echtes Laden).

## Checkliste
- [x] `docs/decisions/029-gemma-gguf-vram-koordination.md` neu. *(bereits in Phase 1 als `docs/decisions/029-gguf-gemma-runtime.md` angelegt — Dateiname weicht leicht ab, Inhalt deckt die AK vollständig.)*
- [x] ADR-028 Nachtrag-Zeile.
- [x] `code-map.md`: Zeile für `inference/gguf_engine.py` + `adapters/gemma_gguf.py`. *(`gguf_engine.py` bereits in Phase 1/2 eingetragen; `adapters/gemma_gguf.py` + `VisionTextGenerator` jetzt ergänzt.)*
- [x] `models.md`: GGUF-Manifest-Eintrag + `format: gguf`-Semantik + optionale mmproj-Datei. *(bereits in Phase 2 im `model_registry`-Schema dokumentiert.)*
- [x] `backend/tests/test_capability_format_routing.py`: Format-Weiche + Vision-Naht (`isinstance`), Registry/Engine gemockt.
- [x] `cd backend && uv run ruff check . && uv run pytest backend/tests/test_capability_format_routing.py` grün.
- [x] STATE.md auf diesen Plan / Abschluss zeigen lassen.

## Report-Back

Docs waren bereits größtenteils aus Phase 1/2 vorhanden (ADR-029, `models.md`-Semantik,
`gguf_engine.py`-Zeile in `code-map.md`) — diese Phase hat nachgezogen: ADR-028-Nachtrag,
`adapters/gemma_gguf.py` + `VisionTextGenerator` in `code-map.md`, und den fehlenden
Format-Weiche/Vision-Naht-Test. Fünf neue Tests, alle grün; ruff sauber.
