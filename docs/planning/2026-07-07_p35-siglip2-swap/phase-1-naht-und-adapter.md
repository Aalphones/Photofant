# Phase 1 — Austausch-Naht + SigLIP2-Adapter + Manifest

**Komplexität:** heikel (Naht-Design + neues Modell-Preprocessing/Tokenizer) · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `backend/photofant/inference/interfaces.py` — `Embedder`-Protokoll (`embed`, `embed_text`). Wird um `dim` erweitert.
- `backend/photofant/inference/adapters/clip.py` — **Vorlage** für den SigLIP-Adapter (zwei ONNX-Sessions über
  `session_manager`, Tokenizer via HF `tokenizers`, L2-Norm, `_pick_embedding`, `_resolve` für `onnx/`-Layout).
- `backend/photofant/inference/preprocessing.py` — hier lebt alles Resize/Normalize. `normalize_clip`,
  `resize_center_crop`, `resize_squash` existieren. **Achtung:** `normalize_clip`s Docstring behauptet fälschlich,
  es sei „für CLIP/SigLIP" — SigLIP braucht **andere** Stats (siehe unten), diese Zeile mit korrigieren.
- `backend/photofant/models/manifest.json` — der `clip-vit-l-14`-Eintrag (`role: "semantic_search"`,
  `hf_repo`, `hf_allow_patterns`) als Vorlage.
- `backend/photofant/models/loader.py` — `load_manifest()`, `ManifestEntry` (Felder `id`, `role`, `hf_repo`,
  `hf_allow_patterns`, `files`, `size_bytes`, `tier`).
- Konsumenten von `resolve_clip_embedder()` (alle umzustellen): `api/search.py` (`_embed_query_text`),
  `classification/engine.py` (`classify_asset`), `jobs/embedding_job.py` (`_run_embedding`).
- Konzept: Dok 040 §2–7 (Capability-Prinzip: Jobs kennen nur Fähigkeiten). Diese Phase realisiert das für Embedding.

## AK der Phase
- [ ] `Embedder`-Protokoll hat `dim: int` (property); `CLIPEmbedder` und `SigLIPEmbedder` liefern es (768 bzw. 1024).
- [ ] **`inference/image_embedder.py`** existiert: `_IMAGE_EMBEDDER_ADAPTERS: dict[str, type[Embedder]]`
      (`"clip-vit-l-14": CLIPEmbedder`, `"siglip2-large-patch16-384": SigLIPEmbedder`) +
      `resolve_image_embedder(role: str = "semantic_search") -> Embedder | None`, das das aktivierte
      `ModelRegistry`-Modell mit Manifest-`role` == `<role>` sucht, die Adapter-Klasse per `manifest_id`
      nachschlägt und mit `entry.path` instanziiert. **Der `role`-Parameter ist Pflicht** (Default
      `semantic_search`) — forward-compat für P37 (`visual_rerank`); nicht auf `"semantic_search"` hart verdrahten.
- [ ] **`inference/adapters/siglip.py`** existiert: `SigLIPEmbedder`, Muster 1:1 wie `CLIPEmbedder`, aber
      `_MANIFEST_ID = "siglip2-large-patch16-384"`, `dim = 1024`, SigLIP-Preprocessing + SigLIP-Text-Kontrakt (unten).
- [ ] **`preprocess_for_siglip(image, size=384)`** in `preprocessing.py`: `resize_squash(image, 384)` +
      neue `normalize_siglip` (mean=[0.5,0.5,0.5], std=[0.5,0.5,0.5]) → NCHW. **Vor Finalisierung** gegen
      `preprocessor_config.json` des heruntergeladenen Repos verifizieren (Resize-Modus + Stats + Size).
- [ ] SigLIP-Text: `_MAX_TEXT_TOKENS = 64`, Padding auf feste Länge 64 (`enable_padding(length=64)` am Tokenizer);
      `attention_mask` nur senden, wenn das ONNX-Text-Modell sie deklariert (Abfrage wie in `clip.py`).
      **Vor Finalisierung** gegen `tokenizer_config.json` (max_length) + die ONNX-Input-Namen verifizieren.
- [ ] Manifest-Eintrag `siglip2-large-patch16-384` (`role: "semantic_search"`, `hf_repo:
      "onnx-community/siglip2-large-patch16-384-ONNX"`, `hf_allow_patterns`: `onnx/vision_model.onnx`,
      `onnx/text_model.onnx`, `tokenizer.json`, `tokenizer_config.json`, `config.json`, `preprocessor_config.json`,
      `tier: "core"`, `license_note` prüfen). CLIP-Eintrag **bleibt** (beide wählbar).
- [ ] Die 3 Konsumenten rufen `resolve_image_embedder()` statt `resolve_clip_embedder()`; letztere Funktion entfällt
      (in `clip.py` nur die Klasse `CLIPEmbedder` behalten).
- [ ] Startup-Guard: beim Server-Start (oder erstem Embed) `vector_index.EMBEDDING_DIM` gegen
      `resolve_image_embedder().dim` prüfen, bei Mismatch **laute** `log.warning` („Vektor-Index-Dim X ≠ Modell-Dim Y
      — Migration + Re-Embed nötig"). Kein Crash.
- [ ] `ruff check .` grün; bestehende Tests grün (ggf. `test_classification_engine.py` nutzt `resolve_clip_embedder`
      als Patch-Ziel → auf `resolve_image_embedder` umstellen).

## Doc-Updates
- [ ] `docs/code-map.md` — Suche-Zeile: `inference/adapters/clip.py` → `+ siglip.py` + `inference/image_embedder.py` (Resolver).
- [ ] `docs/decisions/022-swappable-image-embedder.md` anlegen (Naht + **Swap-Runbook**).
- [ ] `docs/decisions/021-siglip2-embedder.md` anlegen (Variantenwahl + verworfene Alternativen).

## Report-Back
