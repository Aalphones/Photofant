# P9 · Phase 5 — Schwere Captioner

> Rating: standard · Status: pending

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

- [ ] Captioner-Implementierungen (Qwen instruct, JoyCaption guided-Prompt-Builder)
- [ ] Capabilities-Descriptoren + Manifest-Einträge
- [ ] Seed-Presets + Modus-Validierung der Preset-Configs
- [ ] Doc-Update: routes.md, README Features-Stand

## Report-Back
