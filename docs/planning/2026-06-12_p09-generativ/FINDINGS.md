# FINDINGS — P9 Generativ

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>`

## Phase 1 — Spike-Ergebnisse

**diffusers vs. ComfyUI-als-Backend (nicht Trigger):**

diffusers (in-process) gewinnt auf ganzer Linie für den P9-Pfad:
- **VRAM-Koordination:** Im selben Prozess wie ONNX-Sessions → können bei Bedarf evicted werden, bevor ein großes torch-Modell lädt. ComfyUI-als-Backend hätte keine Koordination.
- **Offline-Garantie:** `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` — trivial. ComfyUI müsste separat konfiguriert werden.
- **Komponenten-Modelle:** diffusers-Pipelines laden Transformer, Text-Encoder und VAE nativ aus separaten Pfaden. Passt exakt zum Konzept-§12.1-Picker.
- **fp8/GGUF:** diffusers unterstützt fp8 via torchao/bitsandbytes, GGUF via gguf-Package — beides in der Dependency-Gruppe.
- **P8b deckt ComfyUI ab:** Wer ComfyUI-Workflows nutzen will, hat den Fire-and-Forget-Trigger-Pfad (ADR-003).

Entscheidung dokumentiert in ADR-002.

- [ ] → Phase 2: `ModelRegistry.components` existiert bereits in der DB — die Komponenten-Picker-UI muss das Map-Format `{"transformer": "...", "text_encoder": "...", "vae": "..."}` rendern.
- [ ] → Phase 2: VRAM-Erkennung braucht `torch.cuda.get_device_properties()` — setzt voraus, dass die generative Gruppe installiert ist. Fallback: VRAM = unknown, keine Empfehlung.
- [ ] → Phase 3: SeedVR2 hat keine offizielle diffusers-Pipeline — muss als Custom-Pipeline implementiert oder über ein Community-Package geladen werden. Recherche in Phase 3.
- [ ] → Phase 4: Flux-Edit braucht `FluxImg2ImgPipeline` (diffusers). Inpainting braucht `FluxInpaintPipeline`. Beide existieren in diffusers ≥0.31.
- [ ] → Phase 5: JoyCaption und Qwen-VL sind keine diffusers-Pipelines, sondern transformers-Modelle. Die GenerativeEngine muss auch reine transformers-Pipelines laden können (AutoModelForCausalLM + AutoProcessor).
