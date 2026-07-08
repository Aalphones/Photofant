# ADR-023 — DINOv2 als visueller Re-Ranker

**Status:** Angenommen
**Datum:** 2026-07-08
**Betrifft:** Plan `2026-07-07_p37-dinov2-reranking`, baut auf ADR-022 (swappbare Bild-Embedder-Naht) auf, ergänzt ADR-021 (SigLIP2 als semantischer Embedder)

---

## Kontext

SigLIP2 findet thematisch Passendes (versteht den *Inhalt* eines Bildes), ordnet aber innerhalb
eines Themas nicht nach „sieht aus wie". Für die Bild→Bild-Suche und den Duplikat-Scan zählt aber
genau die *visuelle Erscheinung*: Bildaufbau, Perspektive, Farben, Stil. DINOv2 (self-supervised,
State-of-the-Art für visuelle Ähnlichkeit / Copy-Detection) liefert dieses Signal.

DINOv2 ist **rein visuell** — kein Text-Encoder. Es tritt deshalb als zweiter Embedder neben SigLIP2
in P35s Naht (ADR-022): eigene Rolle `visual_rerank`, eigener Vektorraum, ein aktives Modell pro Rolle.

## Optionen

- **ViT-S/14 (384-dim):** verworfen — der Qualitätssprung ist zu klein, um den Mehraufwand eines
  zweiten Modells + zweiten Vektor-Index zu rechtfertigen.
- **ViT-L/14 (1024-dim):** besseres Retrieval, aber ~3× Parameter/Speicher. Dokumentiert als
  Upgrade-Pfad, falls Qualität später über Ressourcen gestellt wird.
- **ViT-B/14 mit Registers (768-dim) (gewählt):** guter Kompromiss. Re-Ranking von ~100 Kandidaten
  ist zur Suchzeit vernachlässigbar teuer; der reale Kostenfaktor ist Reembed-Zeit + Vektor-Speicher,
  und die RTX 3060 trägt bereits SigLIP2. Die Register-Variante liefert sauberere globale Features als
  das Original ohne Registers (weniger Artefakte in den Attention-Maps).

## Entscheidung

**DINOv2 ViT-B/14 mit Registers, 768-dim.** Bezug als fertiger ONNX-Export
`onnx-community/dinov2-with-registers-base` (`onnx/model.onnx`, 347 MB fp32, self-contained —
kein External-Data-File; Lizenz Apache-2.0, verifiziert 2026-07-08). Kein Selbst-Export nötig.

- Adapter `inference/adapters/dinov2.py` (`DINOv2Embedder`) besitzt Preprocessing und Dim selbst und
  erfüllt das image-only `Embedder`-Protokoll, **nicht** `TextEmbedder`.
- Registriert in `_IMAGE_EMBEDDER_ADAPTERS`; `resolve_image_embedder(role="visual_rerank")` liefert ihn,
  wenn er in der Modelle-UI aktiviert ist. Manifest-Eintrag `dinov2-with-registers-base`.
- **Preprocessing** (gegen `preprocessor_config.json` von `facebook/dinov2-with-registers-base` belegt):
  Resize kürzeste Kante → 256 (bicubic), Center-Crop 224×224, rescale 1/255, ImageNet mean/std.
  Globales Embedding = CLS-Token (`pooler_output`, Fallback `last_hidden_state[:, 0]`).

## Protokoll-Konsequenz: `embed_text` wird eine Fähigkeit

Vor P37 verlangte das `Embedder`-Protokoll `embed_text` von jedem Embedder — DINOv2 kann das nicht.
`Embedder` trägt jetzt nur noch `dim` + `embed` (image-only); ein neues `TextEmbedder(Embedder)`
fügt `embed_text` hinzu. SigLIP2/CLIP erfüllen `TextEmbedder`, DINOv2 nur `Embedder`. Text-Aufrufer
(`api/search.py`, `api/assets.py`, `classification/scoring.py`) prüfen `isinstance(x, TextEmbedder)`,
statt blind zu rufen — die Bauartgrenze „DINOv2 kann keinen Text" ist damit im Typsystem sichtbar.

## Konsequenzen

- **Gut:** Ein Re-Ranker-Tausch bleibt „Adapter + Registry-Zeile + Manifest" (ADR-022). Text-Fähigkeit
  ist type-honest ausgedrückt; ein visueller Embedder kann nicht mehr versehentlich als Text-Encoder
  gerufen werden.
- **Kosten (🟡, einmalig):** Reembed läuft künftig durch **zwei** Modelle (doppelte GPU-Zeit), der
  Vektor-Speicher wächst um einen zweiten 768-dim-Index. Background, blockiert nichts — spürbar beim
  ersten vollen Reembed. Separates Ledger-Flag (Phase 2) lässt nur den DINOv2-Teil nachlaufen.
- Query-Zeit bleibt billig: ein Query-Embed + ~100 Skalarprodukte auf vorberechneten Vektoren.
