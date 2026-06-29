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

- [ ] Sweep + Klassifikation → FINDINGS.md (vor dem Löschen)
- [ ] Backend-Dateien/Routen/JobKinds entfernen
- [ ] Manifest + model-Module bereinigen (Captioner schützen)
- [ ] `pyproject.toml` generative-Deps raus
- [ ] Capabilities-Endpoint anpassen
- [ ] Doc-Update: `code-map.md` (Generativ-Zeile), `routes.md`

## Report-Back
_(beim Umsetzen füllen)_
