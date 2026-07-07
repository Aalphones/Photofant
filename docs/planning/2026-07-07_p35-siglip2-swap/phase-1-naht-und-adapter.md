# Phase 1 — Austausch-Naht + SigLIP2-Adapter + Manifest

**Komplexität:** heikel (Naht-Design + neues Modell-Preprocessing/Tokenizer) · **Status:** complete

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
- [x] `Embedder`-Protokoll hat `dim: int` (property); `CLIPEmbedder` und `SigLIPEmbedder` liefern es (768 bzw. 1024).
- [x] **`inference/image_embedder.py`** existiert: `_IMAGE_EMBEDDER_ADAPTERS: dict[str, type[Embedder]]`
      (`"clip-vit-l-14": CLIPEmbedder`, `"siglip2-large-patch16-384": SigLIPEmbedder`) +
      `resolve_image_embedder(role: str = "semantic_search") -> Embedder | None`, das die aktivierte
      `ModelRegistry`-Zeile mit `role` == `<role>` sucht, die Adapter-Klasse per `manifest_id`
      nachschlägt und mit `entry.path` instanziiert. `role` ist Parameter (Default `semantic_search`).
- [x] **`inference/adapters/siglip.py`** existiert: `SigLIPEmbedder`, Muster 1:1 wie `CLIPEmbedder`, aber
      `_MANIFEST_ID = "siglip2-large-patch16-384"`, `dim = 1024`, SigLIP-Preprocessing + SigLIP-Text-Kontrakt.
- [x] **`preprocess_for_siglip(image, size=384)`** in `preprocessing.py`: `resize_squash(image, 384)` +
      neue `normalize_siglip` (mean/std 0.5) → NCHW. **Verifikation gegen `preprocessor_config.json` offen**
      (Modell noch nicht heruntergeladen → Smoke-Punkt beim User; gegen dokumentierte SigLIP2-Specs gebaut).
- [x] SigLIP-Text: `_MAX_TEXT_TOKENS = 64`, `enable_padding(length=64)` + `enable_truncation(64)`;
      `attention_mask` nur gesendet, wenn das ONNX-Text-Modell sie deklariert. **Verifikation gegen
      `tokenizer_config.json` + echte ONNX-Input-Namen offen** (nach Download → Smoke-Punkt beim User).
- [x] Manifest-Eintrag `siglip2-large-patch16-384` (`role: "semantic_search"`, `hf_repo`,
      `hf_allow_patterns`, `tier: "core"`, `license_note: "Apache 2.0"`). CLIP-Eintrag bleibt.
- [x] **5 statt 3 Konsumenten** rufen `resolve_image_embedder()` (Abweichung, s. Report-Back); `resolve_clip_embedder`
      entfernt, in `clip.py` nur `CLIPEmbedder` behalten.
- [x] Startup-Guard `warn_on_embedding_dim_mismatch()` im Lifespan verdrahtet: `EMBEDDING_DIM` gegen
      `resolve_image_embedder().dim`, laute `log.warning` bei Mismatch, kein Crash.
- [x] `ruff check` auf allen berührten Dateien grün; `test_classification_engine.py` auf
      `resolve_image_embedder` umgestellt, 9/9 grün. (Baseline-Ruff-Fehler in unberührten Dateien s. Report-Back.)

## Doc-Updates
- [x] `docs/code-map.md` — Suche-Zeile: `+ image_embedder.py` (Resolver) + `siglip.py`.
- [x] `docs/decisions/022-swappable-image-embedder.md` angelegt (Naht + **Swap-Runbook**).
- [x] `docs/decisions/021-siglip2-embedder.md` angelegt (Variantenwahl + verworfene Alternativen).

## Report-Back
**Abgeschlossen 2026-07-07.** Naht + SigLIP2-Adapter + Manifest stehen, alle Konsumenten model-agnostisch.

**Abweichung — 2 zusätzliche Konsumenten:** Der Plan listete 3 direkte `resolve_clip_embedder()`-Aufrufer
(`api/search.py`, `classification/engine.py`, `jobs/embedding_job.py`). Ein Grep fand **zwei weitere**:
`classification/scoring.py` (`_embed_prompt_cached`) und `api/assets.py` (`_embed_semantic`). Da
`resolve_clip_embedder` laut AK entfällt, mussten beide mitgezogen werden (sonst ImportError). Alle 5 sind
jetzt auf `resolve_image_embedder()` umgestellt.

**Offen für User-Smoke (Modell nicht lokal):** Preprocessing (Resize/Stats/Size) und Text-Kontrakt
(Padding-Länge/Pad-Token/ONNX-Input-Namen) sind gegen die **dokumentierten** SigLIP2-Specs gebaut, aber
noch nicht gegen die echten `preprocessor_config.json`/`tokenizer_config.json` verifiziert — das geht erst
nach dem Download über die Modelle-UI (Smoke-Checkliste #2/#3 der README).

**Chesterton:** `_MANIFEST_ID` bleibt als dokumentierte Identität in beiden Adaptern erhalten, obwohl nach
Entfernen von `resolve_clip_embedder` kein Code es mehr liest — es benennt, welchen Manifest-Eintrag der
Adapter bedient (Registry-Schlüssel), und spiegelt das Muster über beide Adapter.
