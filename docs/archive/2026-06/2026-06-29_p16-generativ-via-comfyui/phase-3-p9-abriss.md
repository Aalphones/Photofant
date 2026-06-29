# Phase 3 — P9 abreißen (in-process generatives Backend)

**Rating:** standard (Löschen, aber vollständiger Anhängsel-Sweep nötig)

## Kontext (lesen)

- [backend/photofant/api/generative.py](../../../backend/photofant/api/generative.py)
- [backend/photofant/inference/generative_engine.py](../../../backend/photofant/inference/generative_engine.py)
- [backend/photofant/inference/seedvr2_upscaler.py](../../../backend/photofant/inference/seedvr2_upscaler.py)
- [backend/photofant/inference/interfaces.py](../../../backend/photofant/inference/interfaces.py) — Upscaler/Editor/Inpainter-Protocols
- [backend/photofant/jobs/queue.py](../../../backend/photofant/jobs/queue.py) — `JobKind`
- [backend/photofant/models/manifest.json](../../../backend/photofant/models/manifest.json) — Generativ-Rollen/Tier
- [backend/photofant/main.py](../../../backend/photofant/main.py) — Router-Registrierung

## Chesterton's Fence — was P9 tut

P9 ist das in-process-Backend (ADR-002): `GenerativeEngine` lädt eine torch/diffusers-Pipeline,
führt Upscale (SeedVR2), Flux-Edit (img2img) und Inpaint aus, koordiniert VRAM mit den
ONNX-Sessions. Es wird durch ComfyUI vollständig ersetzt (alle drei Aufgaben). **Verstanden:**
nichts davon hat Funktion, die ComfyUI nach P16 nicht abdeckt.

## Akzeptanzkriterien

1. **Vollständiger Rückwärts-Sweep zuerst** (nicht inkrementell): alle Anhängsel von P9 über
   mehrere Namensmuster (`upscale`, `flux`, `inpaint`, `seedvr`, `generative`, `install_generative`)
   in Backend **und** geteilten Modulen erfasst und klassifiziert (gehört zu P9 / bleibt).
   Ergebnis in FINDINGS.md.
2. **Entfernt:** `api/generative.py` (+ Router-Eintrag in `main.py`), `inference/generative_engine.py`,
   `inference/seedvr2_upscaler.py`, `jobs/{upscale,flux_edit,inpaint,install_generative}_job.py`,
   Upscaler/Editor/Inpainter-Protocols in `interfaces.py`, zugehörige `JobKind`-Werte.
3. **Manifest:** nur Bild-Generativ-Rollen (`upscaler`, `editor`, `inpainter`) entfernt.
   **`heavy_captioner` (JoyCaption/Qwen-VL) bleibt** — Kopplung vorher per Code-Check geklärt
   (🟡 README). `models/vram.py`, `loader.py`, `validation.py` von Generativ-Bezügen befreit,
   ohne Captioner-/Core-Pfade zu beschädigen.
4. **Dependencies:** optionale `generative`-Gruppe (torch/diffusers/gguf) aus `pyproject.toml`
   entfernt; `mode-dependencies` beachten.
5. **Capabilities-Endpoint:** `flux_edit`/`inpaint`-Capabilities entfernt oder auf ComfyUI-Status
   umgestellt (Frontend-Konsum in Phase 5).
6. Backend startet, `uv run ruff check .` grün, bestehende Nicht-P9-Tests grün.

## Checkliste

- [x] Sweep + Klassifikation → FINDINGS.md (vor dem Löschen)
- [x] Backend-Dateien/Routen/JobKinds entfernen
- [x] Manifest + model-Module bereinigen (Captioner schützen)
- [x] `pyproject.toml` generative-Deps raus (`diffusers` entfernt, rest bleibt für heavy_captioners)
- [x] Capabilities-Endpoint anpassen
- [x] Doc-Update: `code-map.md` (Generativ-Zeile), `routes.md`

## Report-Back

**Gelöscht:** `api/generative.py`, `inference/seedvr2_upscaler.py`, `jobs/{upscale,flux_edit,inpaint,install_generative}_job.py` (6 Dateien).

**Plan-Abweichung:** `inference/generative_engine.py` bleibt — `qwen_vl` + `joycaption` nutzen `load_transformers_model()`. Nur diffusers-Methoden (`load_pipeline`, `_load_component_model`, `get_pipeline`) entfernt. Dep-Gruppe: nur `diffusers` gestrichen, torch/transformers bleiben.

**Zusätzlich gefunden:** `media/ops.py` hatte `_apply_upscale` + `UpscaleParams` (P9-Code via SeedVR2Upscaler) — ebenfalls entfernt.
