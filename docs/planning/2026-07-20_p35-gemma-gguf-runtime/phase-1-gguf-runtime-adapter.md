# Phase 1 — GGUF-Runtime + Adapter + VRAM-Koordination

**Komplexität:** heikel (zweite Inferenz-Runtime, VRAM-Concurrency, Architektur-Entscheidung ADR-029) · **Status:** pending

## Kontext (lesen, bevor du baust)
- [inference/generative_engine.py](../../../backend/photofant/inference/generative_engine.py) — das torch-Vorbild: `load_transformers_model`, `evict_idle`, `unload`, `_evict_locked`, das `_PipelineEntry`-Muster mit `last_used`, das `threading.Lock`. Die GGUF-Engine spiegelt diese **Form**, nicht den Inhalt.
- [inference/adapters/gemma.py](../../../backend/photofant/inference/adapters/gemma.py) — der torch-Adapter; `GemmaGgufAdapter` spiegelt seine Struktur (`__init__(manifest_id, model_dir)`, `model_id`-Property, `generate`, `resolve_*`-Funktion).
- [inference/interfaces.py:108](../../../backend/photofant/inference/interfaces.py#L108) — `TextGenerator`-Protocol, der einzuhaltende Vertrag. **Und [interfaces.py:82](../../../backend/photofant/inference/interfaces.py#L82) `TextEmbedder(Embedder)`** — das exakte Muster für die neue `VisionTextGenerator(TextGenerator)`-Erweiterung (Fähigkeit per `isinstance` prüfbar, nicht blind aufgerufen).
- [main.py:55-62](../../../backend/photofant/main.py#L55) (Idle-Loop) und [main.py:102](../../../backend/photofant/main.py#L102) (Shutdown).
- `backend/pyproject.toml` Zeilen 29-35 — die `generative`-Extra-Group als Vorbild für eine neue Group.
- Convention: [docs/conventions/python.md](../../../docs/conventions/python.md).

## Architektur-Entscheidung (fällt hier → ADR-029)
**VRAM-Invariante:** genau ein Heavy-Modell resident über beide Runtimes.
**Gewählter Weg — gegenseitiges Cross-Unload (kein abstrakter Arbiter):**
- `GgufEngine.load(...)` ruft **vor** dem `Llama(...)`-Konstruktor `generative_engine.unload()` (torch-Slot leeren) — lazy import innerhalb der Methode gegen Import-Zyklus.
- `GenerativeEngine.load_transformers_model(...)` ruft **vor** dem Laden `gguf_engine.unload()` — ebenfalls lazy import. (Das ist die **einzige** Zeile, die an der bestehenden Engine geändert wird.)
- Beide Runtimes entladen unabhängig per `evict_idle`.

**Alternative (verworfen):** ein `vram_arbiter`-Modul mit registrierten Unload-Callbacks. Sauberer ab **drei** Runtimes, aber für genau zwei ist es Abstraktion ohne Gegenwert — zwei gerichtete Aufrufe sind Chesterton-freundlicher und weniger Code. In ADR-029 als betrachtete Option festhalten.

## AK der Phase
- [ ] `from llama_cpp import Llama` importiert in der neuen Extra-Group; fehlt die Dependency, degradiert `resolve_gemma_gguf` sauber zu `None` (analog `check_generative_available`), kein harter Crash.
- [ ] `GgufEngine` hält genau ein `Llama`-Objekt resident, mit `last_used`, `threading.Lock`, `evict_idle(timeout)`, `unload()` — Form gespiegelt von `GenerativeEngine`.
- [ ] **Vision-Naht in der Engine:** `GgufEngine.load(...)` nimmt einen **optionalen** `mmproj_path: str | None = None`. Ist er gesetzt, wird das `Llama`-Objekt mit dem passenden Vision-Chat-Handler + `clip_model_path=mmproj_path` konstruiert; ist er `None`, lädt reiner Text (unverändert). Den konkreten Gemma-3-Vision-Handler in der Umsetzung ermitteln (llama-cpp-python `llama_chat_format`); trägt die Version ihn nicht, `mmproj_path` ignorieren + **Warnung loggen** (Text läuft weiter) — die Naht bleibt korrekt, siehe README-Risiko.
- [ ] **`VisionTextGenerator(TextGenerator)`** in `interfaces.py` definiert (Muster `TextEmbedder`): `generate_with_image(image: np.ndarray, prompt: str, *, system, max_new_tokens) -> str`. **Kein** Aufrufer nutzt es in dieser Phase.
- [ ] `GemmaGgufAdapter` erfüllt `TextGenerator`: `generate` faltet `system` in den User-Turn (Gemma kennt keine system-Rolle, wie [gemma.py:46-48](../../../backend/photofant/inference/adapters/gemma.py#L46)) und nutzt llama.cpp's `create_chat_completion` (nutzt das eingebettete Chat-Template des GGUF). Ist ein `mmproj` gebunden, erfüllt derselbe Adapter zusätzlich `VisionTextGenerator` (`generate_with_image` reicht Bild + Prompt an den Vision-Handler); ohne mmproj implementiert er nur `TextGenerator`.
- [ ] Cross-Unload in **beide** Richtungen aktiv; die VRAM-Invariante hält (per Smoke #2 nachweisbar).
- [ ] Idle-Loop [main.py:62](../../../backend/photofant/main.py#L62) ruft zusätzlich `gguf_engine.evict_idle(ai_idle_timeout)`; Shutdown [main.py:102](../../../backend/photofant/main.py#L102) ruft zusätzlich `gguf_engine.unload()`.

## Checkliste
- [ ] `backend/pyproject.toml`: neue Extra-Group `gemma-gguf = ["llama-cpp-python>=0.3"]`. Im Kopf-Kommentar der Group den CUDA-Wheel-Install-Weg als Notiz (Plan B für Smoke #1).
- [ ] `interfaces.py`: `VisionTextGenerator(TextGenerator)`-Protocol ergänzen (Muster `TextEmbedder`).
- [ ] `inference/gguf_engine.py` neu: `GgufEngine` (Lifecycle, optionaler `mmproj_path`) + Modul-Singleton `gguf_engine` + `check_gguf_available()`.
- [ ] `inference/adapters/gemma_gguf.py` neu: `GemmaGgufAdapter` (`TextGenerator`, zusätzlich `VisionTextGenerator` bei gebundenem mmproj) + `resolve_gemma_gguf(manifest_id) -> GemmaGgufAdapter | None` (spiegelt `resolve_gemma`: liest `ModelRegistry` inkl. optionalem mmproj-Pfad, entfällt bei disabled/ungebunden).
- [ ] `generative_engine.py`: die eine Cross-Unload-Zeile in `load_transformers_model` (lazy import `gguf_engine`).
- [ ] `main.py`: Idle-Loop + Shutdown um den GGUF-Slot erweitern.
- [ ] `cd backend && uv run ruff check . && uv run mypy photofant/inference/gguf_engine.py photofant/inference/adapters/gemma_gguf.py` grün.

## Report-Back
