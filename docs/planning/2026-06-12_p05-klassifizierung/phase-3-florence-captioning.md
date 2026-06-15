# P5 · Phase 3 — Florence-2-Captioning

> Rating: **heikel** (Konzept §19.6: Generierungs-Loop + Tokenizer auf onnxruntime selbst bauen — aufwändigster ML-Teil) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Presets, Provenienz)
- [Konzept](../../Konzept-Photofant.md) §12.6 (task_token-Modus, Florence-Tabelle), §19.6
- Phase 1 (Interfaces, Executor)

## Akzeptanzkriterien

- Florence-2-base läuft auf onnxruntime: Encoder/Decoder-Sessions, eigener Greedy-/Beam-Search-Loop, Task-Token-Steuerung (`<CAPTION>` / `<DETAILED_CAPTION>` / `<MORE_DETAILED_CAPTION>`), `max_new_tokens` + `num_beams` aus dem Preset.
- **Erlaubter Fallback (Konzept-gedeckt):** `transformers` ausschließlich als Tokenizer-Dependency, kein torch-Import im Core-Pfad. Entscheidung im Report-Back dokumentieren.
- Caption-Job (Ledger `caption_done`), Ergebnis + `captioner` + `caption_preset_id` am Asset.
- `caption_preset`-Migration + Seed-Presets („Kurz", „Detailliert"); Default-Preset je Captioner.
- Durchsatz dokumentiert (Bilder/Minute auf CPU + GPU-Referenz) — Erwartungsmanagement für Bulk-Läufe.

## Checkliste

- [ ] ONNX-Export-Variante wählen (fertige Florence-2-ONNX-Exporte prüfen vs. selbst exportieren) — Findung dokumentieren
- [ ] Generierungs-Loop (KV-Cache-Handling, Beam-Search, Abbruch bei EOS/max_tokens)
- [ ] Tokenizer-Anbindung (Fallback-Regel oben)
- [ ] `caption_preset`-Migration + CRUD-Endpoint + Validierung gegen `caption_mode`
- [ ] Job + Ledger + Dto-Erweiterung; Caption-Sektion im Detail-Panel
- [ ] Doc-Update: docs/models.md (caption_preset)

## Report-Back
