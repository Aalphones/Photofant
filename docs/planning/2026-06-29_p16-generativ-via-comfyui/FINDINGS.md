# FINDINGS — P16 Generativ via ComfyUI

Getaggte Erkenntnisse während der Umsetzung. Format:

- [ ] → Phase N: <Erkenntnis / Abweichung / offene Frage>

---

- [x] → Phase 3: Sweep-Ergebnis (abgehakt nach Einarbeitung):

  **LÖSCHEN komplett:**
  - `api/generative.py` — /generative/status, /install, /unload
  - `inference/seedvr2_upscaler.py` — SeedVR2Upscaler
  - `jobs/upscale_job.py`, `jobs/flux_edit_job.py`, `jobs/inpaint_job.py`, `jobs/install_generative_job.py`

  **ANPASSEN (nicht löschen):**
  - `inference/generative_engine.py`: `load_pipeline()`, `_load_component_model()`, `get_pipeline()` raus —
    `load_transformers_model()` + evict/unload **bleiben** (qwen_vl + joycaption nutzen sie).
  - `inference/interfaces.py`: Upscaler/ImageEditor/Inpainter-Protocols raus.
  - `inference/__init__.py`: generative_engine, ImageEditor, Inpainter, Upscaler aus __all__ raus.
  - `jobs/queue.py`: INSTALL_GENERATIVE/UPSCALE/FLUX_EDIT/INPAINT aus JobKind + _BACKGROUND_PRIORITY raus.
  - `main.py`: generative-Router-Import/-include raus; generative_engine-Lifecycle **bleibt** (heavy captioners).
  - `api/assets.py`: upscale_asset, bulk_upscale_assets, flux_edit_asset, bulk_flux_edit_assets, inpaint_asset + DTOs raus.
  - `api/models.py`: CapabilitiesDto: upscale/flux_edit/inpaint raus; get_capabilities() entsprechend.
  - `models/manifest.json`: flux2-klein-9b, seedvr2-3b, seedvr2-7b raus. qwen+joycaption bleiben.
  - `models/loader.py`: upscaler/editor/inpainter aus _VALID_ROLES raus.
  - `pyproject.toml`: **nur `diffusers>=0.31`** raus. torch/transformers/accelerate/safetensors/sentencepiece **bleiben** (qwen/joycaption).

  **Plan-Abweichung (AK2/AK4):**
  `generative_engine.py` wird nicht vollständig gelöscht — nur die diffusers-Methoden.
  `generative`-Dep-Gruppe bleibt, nur `diffusers` fliegt raus.
  Grund: heavy_captioners (Qwen/JoyCaption) nutzen `load_transformers_model()` + torch/transformers.
- [ ] → Phase 6 (Doku): Prompt-Erkennung nur via Titel-Match (Positive/Negative). Der „Single-Encode-Fallback" (genau ein CLIPTextEncode → positiv, AK1) wurde weggelassen — er kollidiert mit SeedVR2, wo das einzige CLIPTextEncode ein interner Upscaler-Prompt ist. Bewusste Entscheidung: Nutzer benennen Nodes explizit mit Positive/Negative, sonst kein Prompt-Feld. In ADR-008 oder Design-Reconciliation vermerken.
