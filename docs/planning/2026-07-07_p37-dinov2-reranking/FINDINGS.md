# FINDINGS — P37 DINOv2 Re-Ranking

Erkenntnisse während der Umsetzung, getaggt nach Phase. Format:

- [ ] → Phase N: <Erkenntnis / Abweichung / Nachtrag>

---

## Phase 1 — Phase-0-Check (2026-07-08, verifiziert gegen HF-Primärquellen)

- [x] → Phase 1: **ONNX-Export liegt fertig vor, kein Selbst-Export nötig.**
  `onnx-community/dinov2-with-registers-base` → `onnx/model.onnx` (347 MB, fp32, **self-contained**,
  kein External-Data-File, anders als SigLIP2). Vision-only ViT, keine Text-Session. Lizenz **Apache-2.0**
  (bestätigt über HF-API-Metadaten von `facebook/dinov2-with-registers-base`). `hf_allow_patterns`
  begrenzt auf `onnx/model.onnx` + `config.json` + `preprocessor_config.json`; die Quantvarianten
  (fp16/int8/q4/…) bleiben draußen.

- [x] → Phase 1: **Preprocessing (aus `preprocessor_config.json` von `facebook/dinov2-with-registers-base`):**
  Resize kürzeste Kante → **256** (bicubic, resample=3), dann **Center-Crop 224×224**, rescale 1/255,
  **ImageNet**-Normalisierung (mean=[0.485,0.456,0.406] std=[0.229,0.224,0.225]). Unterscheidet sich von
  SigLIP (squash 384², mean/std 0.5) **und** von unserem bisherigen `resize_center_crop` (das resize- und
  crop-Größe gleichsetzt) — DINOv2 braucht resize=256 **≠** crop=224. → `resize_center_crop` um optionalen
  `crop_size` erweitert (rückwärtskompatibel), `normalize_imagenet` existierte schon (Florence nutzt sie).

- [x] → Phase 1: **Globales Embedding = CLS-Token.** `Dinov2Model` legt LayerNorm auf `last_hidden_state`
  und nimmt Token 0 als `pooler_output` (768-dim). Register-Tokens ändern die CLS-Position nicht (CLS bleibt
  Index 0). Adapter bevorzugt `pooler_output`, fällt robust auf `last_hidden_state[:, 0]` zurück (Output-Namen
  des Exports nicht live geprüft — private-Profil, kein Server; der Fallback deckt beide Fälle ab).

- [x] → Phase 1: **Protokoll-Entscheidung — separates `TextEmbedder`-Protokoll** (statt optionaler Methode
  mit Flag). `Embedder` = `dim` + `embed` (image-only, erfüllt DINOv2). `TextEmbedder(Embedder)` fügt
  `embed_text` hinzu (erfüllt SigLIP2/CLIP). Beide `runtime_checkable`. Text-Aufrufer (`api/search.py`,
  `api/assets.py`, `classification/scoring.py`) prüfen `isinstance(embedder, TextEmbedder)` statt blind zu
  rufen — Fähigkeit ist damit ein Typ, kein Flag. Begründung: type-honest, macht die Bauartgrenze
  „DINOv2 kann keinen Text" im Typsystem sichtbar.

- [ ] → Phase 2: Manifest-`id` ist **`dinov2-with-registers-base`** (an `hf_repo` angeglichen, wie bei
  SigLIP), nicht das im Plan skizzierte `dinov2-vitb14-reg`. Adapter-`_MANIFEST_ID` und die Registry-Zeile
  in `image_embedder.py` nutzen denselben Wert — Phase 2 (Ledger/Job) muss auf diese id referenzieren.

- [ ] → Phase 2: DINOv2-Vektor ist **768-dim** (SigLIP2 = 1024). `vec_asset_dino` muss `float[768]` sein,
  getrennt von `vec_asset_embedding` (1024). Adapter `dim = 768` ist die Single Source für die Migration.
