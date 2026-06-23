# P9 — Generative Features (Stage 5)

> Status: geparkt · **optional** · Quelle: [Konzept](../../Konzept-Photofant.md) §8, §12 · Abhängigkeiten: P8 (Versionierung), P4 (Registry), P5 Phase 6 (Settings-Renderer)
>
> **Koexistenz:** Dies ist der **in-process**-Pfad (torch/diffusers, ADR-002). Der **ComfyUI-Trigger-Pfad** (Fire-and-Forget) ist separat als [P8b](../2026-06-15_p08b-comfyui-integration/README.md) geplant (ADR-003) und ersetzt diesen nicht.

GPU-gebundene, vollständig gegatete Features: Upscale (SeedVR2), Flux-Edit (img2img) mit Prompt-Templates, Inpainting, schwere Captioner. Holt den in P4 bewusst ausgeklammerten Modell-Management-Rest nach (Komponenten-Modelle, VRAM-Matrix, Kompatibilitäts-Warnung). Lizenz-Rahmen beachten: FLUX.2 non-commercial (PROJECT.md Constraints).

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Generatives Backend (ADR)](phase-1-generatives-backend.md) | heikel | **complete** |
| 2 | [Komponenten-Modelle & VRAM](phase-2-komponenten-modelle.md) | heikel | **complete** |
| 3 | [Upscale](phase-3-upscale.md) | standard | **complete** |
| 4 | [Flux-Edit & Inpainting](phase-4-flux-edit-inpainting.md) | heikel | **complete** |
| 5 | [Schwere Captioner](phase-5-schwere-captioner.md) | standard | **complete** |

## Kontrakt (Backend ↔ Frontend)

- **`POST /api/assets/{id}/upscale`** — `{ model_id, params }`; **`POST /api/assets/{id}/flux-edit`** — `{ prompt | template_id, params (strength/steps/guidance/seed) }`; **`POST /api/assets/{id}/inpaint`** — `{ mask (PNG base64/upload), prompt, params }`. Alle: Queue-Jobs, Ergebnis als neue `version` (P8-Kette), bulk-fähig über den Bulk-Edit-Pfad (außer Inpaint — single only).
- **`GET/POST/PATCH/DELETE /api/prompt-templates`** — CRUD nach Konzept §5/§8.4; `{person}`-Platzhalter wird beim Anwenden ersetzt.
- **Registry-Erweiterung:** `register-local` akzeptiert `components`-Map (`{ diffusion, text_encoder, vae }`, getrennte Pfade); Download-Flow lädt Varianten (bf16/fp8/GGUF) inkl. Begleitdateien; Capabilities-Endpoint um `upscale`, `flux_edit`, `inpaint`, `heavy_caption` erweitert.
- **Validierungs-Erweiterung (§12.2a Stufe 6):** Kompatibilitäts-**Warnung** (Encoder-/VAE-Familie laut Manifest) — Warnung mit „trotzdem verwenden", **kein** hartes Gate (§19.7); neuer Code `MODEL_COMPONENT_MISMATCH` (warning-level), `MODEL_VRAM_EXCEEDED` (Empfehlung).
- **Offline-Garantie:** Aktivierung eines torch-Modells setzt `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1` im Prozess; torch/diffusers als optionale Dependency-Gruppe, Installation über die UI angestoßen und erklärt.

## Finale Akzeptanzkriterien

1. ADR-002 dokumentiert die Backend-Wahl (diffusers vs. ComfyUI) nach Spike; die Implementierung folgt ihr.
2. Flux als Komponenten-Modell einbindbar: drei getrennte Picker, Pfade dürfen verstreut liegen; Feature bleibt zu, bis alle drei Teile gesetzt sind; inkompatible Familie → Warnung, kein Block.
3. VRAM-Erkennung empfiehlt eine Variante (Matrix §12.4); Download der gewählten Variante inkl. Begleitdateien; fp8 **und** GGUF laden nachweislich.
4. Upscale erzeugt eine Version (Foto-Tausch über `is_current`), Face-Dedupe-Upscale-Regel aus §8.3 greift (`is_upscaled`, alter Crop als überholt).
5. Flux-Edit mit Template (inkl. `{person}`) und freiem Prompt; Inpainting mit im Editor gemalter Maske; Seeds reproduzierbar in `version.params`.
6. JoyCaption/Qwen-VL als Captioner wählbar; Settings-Panels rendern deklarativ aus dem Capabilities-Descriptor (`instruct` / `instruct_guided` nach §12.6) — ohne neuen Renderer.
7. Ohne GPU/Modelle: alles sauber gegated mit Hinweis, Rest der App unbeeinträchtigt.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Vorhandenen ComfyUI-Flux-Bestand in-place einbinden (3 Picker) → Feature schaltet frei
- [ ] Absichtlich falschen Text-Encoder wählen → Warnung erscheint, „trotzdem verwenden" möglich
- [ ] Foto upscalen → Version da, Grid zeigt Upscale, zurückwechselbar
- [ ] Flux-Edit mit Template auf 3 Bildern (bulk) → Ergebnisse als Versionen, Seed in den Params
- [ ] Objekt per Inpainting entfernen → Maske gemalt, Ergebnis plausibel
- [ ] Caption mit JoyCaption (Booru-Preset) erzeugen → Stil entspricht Preset

## Summary

P9 vollständig abgeschlossen. Alle 5 Phasen implementiert: generatives Backend (ADR-002), Komponenten-Modelle + VRAM-Matrix, Upscale (SeedVR2), Flux-Edit + Inpainting, schwere Captioner (Qwen2.5-VL + JoyCaption).

## Files touched

Backend: `generative_engine.py`, `caption_config.py`, `caption_job.py`, `manifest.json`, neue Adapter `qwen_vl.py`/`joycaption.py`, Migration `0021_seed_heavy_captioner_presets.py`. Frontend: `angular.json` (Budget), `lightbox.html` (TS-Fix), `editor.ts` (TS-Fix).

## Commits

Alle Phasen einzeln committed auf master.

## Deviations from plan

- JoyCaption und Qwen-VL nutzen `GenerativeEngine.load_transformers_model()` statt `load_pipeline()` (Finding Phase 1 umgesetzt).
- Seed-Presets als model_id=NULL angelegt (Modell-Registrierung kommt erst zur Laufzeit).
- CSS-Budget in angular.json erhöht (pre-existing, nicht P9 verursacht).

## Follow-ups

- JoyCaption: Lizenzcheck vor Produktion (LLaMA-Basis mit JoyCaption Fine-Tune).
- Qwen2.5-VL: `min_pixels`/`max_pixels` direkt als Bild-Processing-Parameter testen.
- Frontend-UI für instruct/instruct_guided Preset-Builder (deklarativer Settings-Renderer aus P5).
- Smoke-Checkliste: Caption mit JoyCaption (Booru-Preset) nach Modell-Download testen.
