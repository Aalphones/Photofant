# Phase 3 — Two-Stage Re-Ranking in der Bild→Bild-Suche

**Komplexität:** heikel (Rerank-Naht, saubere Degradation bei Text/ohne Modell) · **Status:** ✅ complete

## Kontext (vor dem Bauen lesen)
- `backend/photofant/api/search.py` — `POST /api/search/semantic`: Text-Pfad (`_embed_query_text`) **und**
  `like_asset_id`-Pfad. Ruft `vector_index.search()` (SigLIP2-KNN). **Hier** hängt der Rerank für `like_asset_id`.
- `backend/photofant/api/search.py` bzw. der `by-image`-Endpoint aus **P36** (falls schon gebaut) — der Upload-Pfad,
  zweiter Rerank-Ort. Ist P36 noch nicht da, greift der Rerank nur bei `like_asset_id`; der Upload-Pfad zieht später nach.
- `backend/photofant/db/vector_index.py` — `search()` (liefert die Top-N Kandidaten) + Zugriff auf `vec_asset_dino`
  (aus Phase 2), um die DINOv2-Vektoren der Kandidaten zu laden.
- `backend/photofant/inference/image_embedder.py` — `resolve_image_embedder(role="visual_rerank")` für den
  DINOv2-Query-Vektor (bei Upload: on-the-fly; bei `like_asset_id`: der vorberechnete `dino_embedding` des Quell-Assets).

## Die Rerank-Naht
Neu: **`search/rerank.py`** (o.ä.) — `rerank_by_appearance(query_dino_vec, candidate_ids, top_k) -> list[(id, score)]`.
- Lädt die `dino_embedding`-Vektoren der `candidate_ids` (aus `vec_asset_dino` bzw. den BLOBs).
- Cosine zwischen `query_dino_vec` und jedem Kandidaten → absteigend sortiert → Top-`k`.
- **Reine Funktion, ohne HTTP/DB-Verflechtung** über den Vektor-Zugriff hinaus → isoliert testbar.

Ablauf im `like_asset_id`-Pfad:
1. SigLIP2-KNN → Top-`candidatePoolSize` (Default 100) Kandidaten-IDs.
2. DINOv2-Query-Vektor bestimmen: Quell-Asset hat `dino_embedding`? → laden. Nicht vorhanden → **Schritt 4** (Fallback).
3. `rerank_by_appearance(...)` → Top-`k` (Default 10). Fertig.
4. **Fallback (kein Rerank):** kein DINOv2-Modell aktiv **oder** `rerank.enabled=false` **oder** kein Query-Bild
   **oder** Quell-/Kandidaten-DINOv2-Vektoren fehlen → SigLIP2-Reihenfolge unverändert zurückgeben.

## AK der Phase
- [x] **Text-Pfad unangetastet:** `_embed_query_text`-Suche läuft exakt wie vor P37 (kein Rerank, kein neuer Code im
      Hot-Path). Explizit belegt (`test_text_query_never_reranks`).
- [x] `rerank_by_appearance(...)` existiert als isoliert getestete Funktion (Cosine-Sort korrekt, leere/teilbesetzte
      Kandidatenmenge robust). Reiner Kern `_rank_by_cosine` DB-frei getestet, `rerank_by_appearance` gegen Temp-DB.
- [x] `like_asset_id`-Suche liefert DINOv2-re-gerankte Top-`k`, wenn Rerank aktiv **und** Query-DINOv2-Vektor vorhanden.
- [x] **Degradation lückenlos:** je Fallback-Bedingung (Modell aus / Setting aus / Text-Query / fehlende Vektoren)
      kommt das reine SigLIP2-Ergebnis ohne Fehler zurück. Je Zweig ein Test (5 Degradations-Tests).
- [x] Settings `rerank.enabled` (true) + `rerank.candidate_pool_size` (100) gelesen und wirksam; über die
      Verarbeitungs-Seite (Gruppe „Bildähnliche Suche") einstellbar. **Naming:** snake_case `candidate_pool_size`
      (konsistent mit `reverse_search`), nicht das im Plan skizzierte camelCase — im Frontend nested gemappt.
- [x] P36s `by-image`-Endpoint existiert → derselbe Rerank greift dort mit dem on-the-fly DINOv2-Vektor des
      Upload-Bilds (`resolve_image_embedder(role="visual_rerank")`).
- [x] `ruff check .` grün (meine Dateien; 6 vorbestehende Fehler in fremden Dateien — s. Report-Back); Tests grün (15).

## Doc-Updates
- [x] `docs/decisions/024-two-stage-rerank.md` — Ablauf, Pool-Größe, Fallback-Matrix ausgeführt.
- [x] `docs/routes.md` / `docs/code-map.md` — Rerank-Funktion + Such-Pfad ergänzt.

## Report-Back

**Umgesetzt (2026-07-08):**
- **Backend:** `settings.py` (nested `rerank`-Gruppe: `enabled`/`candidate_pool_size`) ·
  `db/vector_index.py` (`load_dino_embeddings` — Kandidaten-Vektoren aus `asset.dino_embedding`-BLOBs) ·
  neues Paket `search/rerank.py` (`_rank_by_cosine` pur + `rerank_by_appearance`) ·
  `api/search.py` (Rerank in `like_asset_id` + `by-image`, Helfer `_dino_embedding_for_asset` /
  `_embed_upload_dino` / `_rerank_pool`).
- **Frontend:** `config.model.ts` + `models.effects.ts` (nested rerank snake↔camel) + Verarbeitungs-Seite
  (Toggle + Kandidaten-Pool-Feld, Gruppe „Bildähnliche Suche").
- **Tests:** `test_search_rerank.py` (15 grün — pur/DB/Wiring/5 Degradationszweige), `test_search_by_image.py`
  Settings-Helper nachgezogen.

**Design-Entscheidungen:**
- Rerank operiert auf dem **aktiv-gefilterten Pool**: erst SigLIP-Kandidaten, dann active/exclude/min_score
  filtern, dann re-ranken, dann auf `limit` kürzen — Kandidaten ohne DINOv2-Vektor landen in SigLIP-Reihenfolge
  hinten, das Ergebnis schrumpft nie.
- `like_asset_id` braucht **kein** DINOv2-Modell zur Suchzeit (Vektoren sind vorberechnet); nur der Upload-Pfad
  embedded on-the-fly und degradiert bei fehlendem Modell.

**🟡 Baseline-Rot (nicht von dieser Phase):** 13 Backend-Tests (comfyui/caption) + 6 ruff-Fehler (Migrationen,
`assets.py`, `comfyui_run_job.py`) waren **schon auf `ab1ed58` rot** (per git-stash verifiziert). Außerhalb Scope.
