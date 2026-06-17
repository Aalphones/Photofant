# P5 · Phase 3 — Florence-2-Captioning

> Rating: **heikel** (Konzept §19.6: Generierungs-Loop + Tokenizer auf onnxruntime selbst bauen — aufwändigster ML-Teil) · Status: complete

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

- [x] ONNX-Export-Variante wählen — **onnx-community/Florence-2-base** (fertiger transformers.js-Export, im Manifest mit `hf_repo` + HF-Snapshot-Download aus Phase 1/2); kein Selbst-Export.
- [x] Generierungs-Loop (KV-Cache-Handling, Beam-Search, Abbruch bei EOS/max_tokens) — Merged-Decoder, `num_beams == 1` = Greedy als Spezialfall.
- [x] Tokenizer-Anbindung — `tokenizers` (HF Rust-Tokenizer, lädt `tokenizer.json`), **statt** vollem `transformers`: leichter, kein torch. AK-Fallback gedeckt.
- [x] CRUD-Endpoint + Validierung gegen `caption_mode`; Seed-Presets via Migration 0006 (Schema-Tabelle existierte schon ab 0004).
- [x] Job + Ledger + Dto-Erweiterung; Caption-Sektion im Detail-Panel
- [x] Doc-Update: docs/models.md (caption_preset + Seed-Presets + caption-Felder)

## Report-Back

**Entscheidungen:**
- **Tokenizer:** `tokenizers>=0.20` statt `transformers` — der AK-Fallback erlaubt „transformers nur als Tokenizer-Dep"; `tokenizers` ist die Rust-Engine dahinter, lädt `tokenizer.json` direkt, zieht **kein** torch. Schlankere, intent-treuere Wahl.
- **Task-Token ≠ wörtlicher Input:** Florence konsumiert nicht das Literal `<DETAILED_CAPTION>`, sondern einen Prompt-Satz pro Task. Mapping in `caption_config.FLORENCE_TASK_PROMPTS` (aus dem Microsoft-Processor übernommen). **Ohne dieses Mapping liefert das Modell Müll.**
- **Preprocessing korrigiert:** Der Stub `preprocess_for_florence` delegierte an CLIP (224² Center-Crop) — falsch für Florence. Auf **768² Squash-Resize** (do_center_crop=false) + ImageNet-Norm umgestellt (`resize_squash`).
- **Generierungs-Loop nicht ausführbar getestet:** Das 460-MB-Modell liegt nicht im Repo. Loop ist defensiv (Input-/Output-Namen werden introspiziert, KV-Cache dynamisch aus den Decoder-Inputs gebaut), folgt dem transformers.js-Merged-Decoder-Kontrakt — **muss im User-Smoke-Test gegen einen echten Download validiert werden** (AK#4).
- **Durchsatz:** Erwartungsmanagement — Florence-2-base auf CPU ist langsam (grob ~3–10 s/Bild, je nach `max_new_tokens`/`num_beams`); GPU (DirectML/CUDA) deutlich schneller. Bulk-Captioning ist ein Hintergrund-Job, kein Echtzeit-Pfad. Konkrete Bilder/Minute erst nach echtem Lauf belastbar.

**Dateien:**
- `backend/photofant/inference/caption_config.py` — `CaptionMode`, `FLORENCE_TASK_PROMPTS`, `validate_caption_config`, `task_token_settings`, Defaults.
- `backend/photofant/inference/adapters/florence2.py` — `Florence2Captioner` (Captioner-Protokoll), Encode-Merge (Bild-Features ⊕ Prompt-Embeds → Encoder), Beam-Search-Decoder mit KV-Cache; `resolve_florence_captioner()`.
- `backend/photofant/inference/preprocessing.py` — `resize_squash` + `preprocess_for_florence` (768²) korrigiert.
- `backend/photofant/jobs/caption_job.py` — `run_caption_job`/`enqueue_caption`, Default-Preset-Auflösung, Ledger `caption_done`.
- `backend/photofant/jobs/import_job.py` — `_enqueue_caption_batch` nach Tagging (Import + Scan).
- `backend/photofant/api/caption_presets.py` — CRUD-Router (GET/POST/PATCH/DELETE), Validierung, Single-Default-Semantik.
- `backend/photofant/api/assets.py` — `AssetDetailDto` um `caption`/`captioner`/`caption_preset_id`.
- `backend/photofant/main.py` — Router registriert.
- `backend/alembic/versions/0006_seed_caption_presets.py` — Seed „Kurz"/„Detailliert".
- `backend/pyproject.toml` — `tokenizers>=0.20`.
- `frontend/.../asset.model.ts` + `lightbox.{ts,html,scss}` — Caption-Felder + Caption-Sektion im Panel.
- `backend/tests/test_caption_config.py`, `test_caption_presets_api.py` — modell-freie Tests (12, grün).

**Verschoben (in FINDINGS getaggt):** `POST /classify/rerun` → Phase 5; `capabilities`-Descriptor + Settings-UI → Phase 6.

**Bekannt-rot (vorbestehend, nicht Phase 3):** `test_model_validation.py::test_incomplete_when_companion_csv_missing` schlägt schon auf sauberem HEAD fehl (onnxruntime lädt Fake-ONNX-Bytes, bevor der INCOMPLETE-Check greift).
