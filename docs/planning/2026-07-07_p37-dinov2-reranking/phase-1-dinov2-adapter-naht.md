# Phase 1 — DINOv2-Adapter + image-only-Naht + Manifest

**Komplexität:** heikel (Protokoll-Aufweichung + neues Preprocessing/ONNX-Export-Check) · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `backend/photofant/inference/interfaces.py` — `Embedder`-Protokoll (P35-Endzustand: `embed`, `embed_text`, `dim`).
  Hier wird `embed_text` **optional** — Text-Fähigkeit wird zur Eigenschaft, nicht zur Pflicht.
- `backend/photofant/inference/adapters/siglip.py` (aus P35) — **Vorlage** für den DINOv2-Adapter, aber DINOv2 hat
  **nur** eine Vision-Session, keinen Text-Encoder. Die Text-Teile fallen weg.
- `backend/photofant/inference/image_embedder.py` (aus P35) — `resolve_image_embedder(role=...)` + Adapter-Registry.
  DINOv2 wird hier registriert.
- `backend/photofant/inference/preprocessing.py` — `resize_squash`, `resize_center_crop`, `normalize_siglip`
  (aus P35). Neu: DINOv2-Preprocessing mit **ImageNet-Stats**.
- `backend/photofant/models/manifest.json` — der `siglip2-large-patch16-384`-Eintrag als Vorlage.
- `backend/photofant/models/loader.py` — `ManifestEntry` (`id`, `role`, `hf_repo`, `hf_allow_patterns`, `files`, …).
- **Alle `embed_text`-Aufrufer** (müssen nach der Optionalisierung noch kompilieren/laufen): `api/search.py`
  (`_embed_query_text`), ggf. `classification/engine.py`. Zuerst greppen: `grep -rn "embed_text" backend/`.

## Phase-0-Check (vor dem Adapter, blockierend)
- [ ] **ONNX-Export sichten:** existiert ein brauchbarer DINOv2-Vision-ONNX-Export (mit Registers, 768-dim)?
      HF/onnx-community prüfen. Ergebnis in FINDINGS notieren. Falls nein → Selbst-Export (opset, dynamische
      Batch-Achse) als zusätzlicher Schritt dieser Phase, Aufwand dort vermerken.
- [ ] **Preprocessing verifizieren:** `preprocessor_config.json` + Modell-Card lesen — Resize-Größe (224/256?),
      Normalisierung (ImageNet mean=[0.485,0.456,0.406] std=[0.229,0.224,0.225]), und **wie das globale Embedding
      entsteht** (CLS-Token vs. mean-pooling der Patch-Tokens). Das ist die Wackelstelle für stumpfe Vektoren.

## AK der Phase
- [ ] `Embedder`-Protokoll: `embed_text` ist **optional** (eigenes `TextEmbedder`-Protokoll, das `Embedder` erweitert,
      **oder** `embed_text` als optionale Methode mit Fähigkeits-Flag). Entscheidung + Begründung in FINDINGS.
      SigLIP2/CLIP erfüllen weiterhin die Text-Fähigkeit; DINOv2 erfüllt sie **nicht**.
- [ ] **`inference/adapters/dinov2.py`** existiert: `DINOv2Embedder` — eine Vision-ONNX-Session über `session_manager`,
      `_MANIFEST_ID = "dinov2-vitb14-reg"` (o.ä., an den Manifest-Eintrag angeglichen), `dim = 768`, L2-Norm,
      `_resolve` für das `onnx/`-Layout. **Kein** `embed_text`.
- [ ] **`preprocess_for_dinov2(image)`** in `preprocessing.py`: Resize + Center-Crop auf die verifizierte Größe +
      neue `normalize_imagenet` (ImageNet mean/std) → NCHW. Gegen `preprocessor_config.json` belegt.
- [ ] DINOv2 in `_IMAGE_EMBEDDER_ADAPTERS` registriert; `resolve_image_embedder(role="visual_rerank")` liefert ihn,
      wenn das DINOv2-Modell in der Modelle-UI aktiviert ist.
- [ ] Manifest-Eintrag `dinov2-vitb14-reg` (`role: "visual_rerank"`, `hf_repo` = der in Phase-0 bestätigte Export,
      passende `hf_allow_patterns`, `tier`, `license_note` = Apache-2.0 prüfen).
- [ ] `ruff check .` grün; bestehende Tests grün (SigLIP2/CLIP-Text-Pfade laufen nach der Protokoll-Änderung weiter).

## Doc-Updates
- [ ] `docs/code-map.md` — Suche-Zeile um `inference/adapters/dinov2.py` ergänzen.
- [ ] `docs/decisions/023-dinov2-visual-rerank.md` anlegen (Variantenwahl + verworfene Alternativen + ONNX-Herkunft).
- [ ] `docs/decisions/024-two-stage-rerank.md` anlegen (Naht-Prinzip; Rerank-Details folgen in Phase 3).

## Report-Back
