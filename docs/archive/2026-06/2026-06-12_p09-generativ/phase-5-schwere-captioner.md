# P9 · Phase 5 — Schwere Captioner

> Rating: standard · Status: **complete** (2026-06-23)

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Capabilities-Erweiterung)
- [Konzept](../../Konzept-Photofant.md) **§12.6 (instruct + instruct_guided Tabellen)**, §12.3 (JoyCaption/Qwen-Einträge)
- P5 Phase 6 (deklarativer Settings-Renderer — wird nur mit Descriptoren gefüttert)

## Akzeptanzkriterien

- Qwen2.5-VL (`instruct`) und JoyCaption (`instruct_guided`) als Captioner-Implementierungen (torch, gated); Settings-Panels entstehen rein aus den Capabilities-Descriptoren nach den §12.6-Tabellen (System-Prompt/Sampling bzw. Baustein-Builder + Raw-Override) — der P5-Renderer bleibt unangetastet.
- Presets funktionieren modellübergreifend wie in P5 (Provenienz via `caption_preset_id`); Seed-Presets je Modell („Natürliche Sprache", „Booru-Stil").
- Caption-Lauf mit schwerem Modell läuft über die generative Job-Klasse (VRAM-Schutz); Florence bleibt Default.
- Info-Boxen aus §12.6 (Qwen: tag-geflavorte Prosa ≠ echte Booru-Taxonomie) wörtlich übernehmen.

## Checkliste

- [x] Captioner-Implementierungen (Qwen instruct, JoyCaption guided-Prompt-Builder)
- [x] Capabilities-Descriptoren + Manifest-Einträge
- [x] Seed-Presets + Modus-Validierung der Preset-Configs
- [x] Doc-Update: routes.md, README Features-Stand

## Report-Back

**Status: complete (2026-06-23)**

Neue Dateien:
- `backend/photofant/inference/adapters/qwen_vl.py` — Qwen2.5-VL-7B-Instruct Adapter (`instruct`)
- `backend/photofant/inference/adapters/joycaption.py` — JoyCaption Alpha Two Adapter (`instruct_guided`)
- `backend/alembic/versions/0021_seed_heavy_captioner_presets.py` — Seed-Presets (je 2 pro Modell)

Geänderte Dateien:
- `caption_config.py` — Validatoren für `instruct` + `instruct_guided` freigeschaltet
- `generative_engine.py` — `load_transformers_model()` für reine transformers-Modelle
- `caption_job.py` — Multi-Captioner-Dispatch; heavy Captioner werden bevorzugt
- `manifest.json` — Einträge für `qwen2-5-vl-7b` und `joycaption-alpha-two` inkl. Capabilities-Descriptor

FINDING aus Phase 1 ([x]) eingearbeitet: GenerativeEngine unterstützt jetzt auch reine transformers-Modelle.
