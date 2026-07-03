# Phase 2 — Engine: CLIP + WD14-Fusion, Job, Pipeline-Hook

**Tier:** heikel (Fusions-Algorithmus, Queue-Nebenläufigkeit, Reuse gespeicherter Daten)

## Kontext (vor Start lesen)

- [`backend/photofant/inference/adapters/clip.py`](../../../backend/photofant/inference/adapters/clip.py) — `embed_text()` liefert L2-normalisierte 768-dim-Vektoren; `resolve_clip_embedder()` gibt `None`, wenn das Modell nicht aktiv ist.
- [`backend/photofant/db/vector_index.py`](../../../backend/photofant/db/vector_index.py) — wie Embeddings serialisiert/gelesen werden (`np.frombuffer(blob, np.float32)`).
- [`backend/photofant/jobs/heuristics_job.py`](../../../backend/photofant/jobs/heuristics_job.py) — Muster für einen Per-Asset-Job mit Ledger-Flag + `asyncio.to_thread`.
- [`backend/photofant/jobs/queue.py`](../../../backend/photofant/jobs/queue.py) — `JobKind`, `_BACKGROUND_PRIORITY` (Face vor Tagging/Embedding vor Captioning), Drei-Spuren-Modell.
- [`backend/photofant/jobs/rerun_job.py`](../../../backend/photofant/jobs/rerun_job.py) + [`api/classify.py`](../../../backend/photofant/api/classify.py) — wie Rerun-Schritte über Ledger-Flags gesteuert werden.
- Import-Pipeline-Einstieg: [`backend/photofant/jobs/import_job.py`](../../../backend/photofant/jobs/import_job.py) + [`jobs/embedding_job.py`](../../../backend/photofant/jobs/embedding_job.py), [`jobs/tagging_job.py`](../../../backend/photofant/jobs/tagging_job.py) — wo nachgelagerte Jobs enqueued werden.
- Bestehende Engine-Muster: [`backend/photofant/collections/engine.py`](../../../backend/photofant/collections/engine.py).

> **Voraussetzung:** Die settings.json-Keys aus der README sind von Sascha freigegeben, bevor diese Phase startet (Critical Rule 7).

## Akzeptanzkriterien

1. `classification/engine.py` implementiert `classify_asset(session, asset_id)`
   exakt nach Kontrakt-Signatur (README): liest `asset.clip_embedding` + die
   gespeicherten `asset_tag.score`-Werte, **lädt kein Bild und ruft kein
   Vision-Modell**. Gibt `list[ClassificationResult]` zurück, kein commit.
2. CLIP-Label-Scoring: Prompt-Texte je Label werden embedded (Text-Embeddings
   per `lru_cache` über den Prompt-String gecacht), je Label gemittelt, Cosinus
   zum Bild-Embedding, **softmax über die Labels einer Kategorie** → Wahrscheinlichkeit.
3. WD14-Signal: `max` der gespeicherten Tag-Scores über `label.wd14_tags`; fehlt
   der Tag → kein WD14-Signal, Fusion nutzt nur CLIP (Quelle `clip` statt `fused`).
4. Fusion + Entscheidung nach Kontrakt: gewichteter Schnitt (`clip_weight`/`wd14_weight`),
   single-Kategorie = argmax über `min_confidence`, multi-Kategorie = alle über
   `multi_min_confidence`. Per-Kategorie-`min_confidence` überschreibt die globale Schwelle.
5. Ist CLIP nicht aktiv (`resolve_clip_embedder()` → `None`): Engine arbeitet
   WD14-only weiter (kein Crash), Labels ohne WD14-Tag entfallen.
6. `jobs/classification_job.py`: `run_classification_job` persistiert
   (ersetzt die `asset_classification`-Zeilen des Assets atomar), setzt
   `ProcessingLedger.classified = True`. `enqueue_classification(asset_id)`
   läuft in der **Background-Queue** nach Embedding+Tagging.
7. Import-Pipeline: nach `embedding_done` **und** `tags_done` wird die
   Klassifizierung automatisch enqueued (genau einmal pro Content-Hash via Ledger).
8. Rerun: `ClassifyStep` um `"categories"` erweitert; `rerun_job` setzt
   `classified=False` zurück und enqueued `classification_job`.
9. `ruff` grün; Unit-Test deckt die Fusions-Entscheidung ab (single argmax,
   multi-Schwelle, WD14-Fallback, CLIP-aus-Fallback) — table-driven.

## Checkliste

- [x] `classification/engine.py`: `ClassificationResult` (dataclass) + `classify_asset`.
- [x] `classification/scoring.py` (oder in `inference/`): `score_labels(image_emb, prompts_per_label)` mit Text-Embedding-Cache + Softmax je Kategorie.
- [x] `jobs/classification_job.py`: Per-Asset-Job + `enqueue_classification` + Batch-Enqueue-Helfer für den Retro-Lauf (Selektion/„all").
- [x] `jobs/queue.py`: `JobKind.CLASSIFICATION` + Position in `_BACKGROUND_PRIORITY` (nach Embedding/Tagging).
- [x] Import-Hook: in `embedding_job`/`tagging_job` (oder Orchestrierung) Klassifizierung anstoßen, sobald beide Vorbedingungen erfüllt sind.
- [x] `api/classify.py`: `"categories"` zu `ClassifyStep`; `rerun_job.py` Mapping + Ledger-Reset.
- [x] Settings-Zugriff über `load_settings()` für die fünf Keys (keine Magic Numbers).
- [x] Tests: `backend/tests/test_classification_engine.py` (Fusions-Tabelle).

## Report-Back

**Umgesetzt wie geplant** — Kontrakt-Signatur, Fusionsformel und HTTP-Anbindung
1:1 aus der README übernommen, keine Abweichungen.

- **Engine** (`classification/engine.py` + `classification/scoring.py`): liest
  `asset.clip_embedding` + gespeicherte `asset_tag.score`-Werte, lädt nie ein
  Bild, ruft nie ein Vision-Modell. CLIP-Prompt-Text-Embeddings werden per
  `lru_cache` prozessweit gecacht. Fallback-Kette: CLIP inaktiv **oder** Asset
  hat kein gespeichertes Embedding → WD14-only (kein Crash); Label ohne
  passenden WD14-Tag → clip-only; beide da → gewichtete Fusion.
- **Job + Pipeline-Hook**: `jobs/classification_job.py` (idempotent — ersetzt
  die `asset_classification`-Zeilen des Assets atomar, setzt
  `ProcessingLedger.classified`). Neue `jobs/classification_pipeline.py`
  (Kopie des `face_pipeline`-Musters) wartet auf Tagging **und** Embedding und
  enqueued Klassifizierung genau einmal pro Asset — verdrahtet in
  `tagging_job.py`/`embedding_job.py` (Signal auch im Skip-Pfad, falls WD14/CLIP
  deaktiviert) und `import_job._enqueue_pipeline` (Prereq-Count wie beim
  Face-Pattern: `int(auto_tag) + int(auto_embed)`).
- **Rerun**: `"categories"` als neuer `ClassifyStep` in `api/classify.py` +
  `rerun_job.py` (Ledger-Reset via `_STEP_FLAGS["categories"] = "classified"`,
  läuft nach dem `"embedding"`-Schritt in derselben Iteration).
- **Settings**: `classification.*`-Keys in `Data/.photofant/settings.json` +
  `photofant/settings.py` (Defaults, Typen, Merge) ergänzt — von Sascha vorab
  freigegeben (Critical Rule 7).
- **Tests**: 9 table-driven Fälle in `test_classification_engine.py` — single
  argmax (über/unter Schwelle), multi-Schwelle, WD14-Fallback, CLIP-aus-Fallback,
  fehlendes Embedding, Kategorie-Override der Schwelle, ein Ende-zu-Ende-Fall
  mit echtem WD14-Score (nicht gemockt). `ruff` grün, volle Backend-Suite läuft
  (13 vorbestehende, unabhängige ComfyUI/Caption-Config-Fails unverändert —
  vor dieser Phase verifiziert, nicht Teil dieser Phase).
