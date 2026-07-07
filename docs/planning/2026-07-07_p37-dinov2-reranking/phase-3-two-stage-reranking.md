# Phase 3 — Two-Stage Re-Ranking in der Bild→Bild-Suche

**Komplexität:** heikel (Rerank-Naht, saubere Degradation bei Text/ohne Modell) · **Status:** pending

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
- [ ] **Text-Pfad unangetastet:** `_embed_query_text`-Suche läuft exakt wie vor P37 (kein Rerank, kein neuer Code im
      Hot-Path). Explizit belegt (Test oder Smoke #3).
- [ ] `rerank_by_appearance(...)` existiert als isoliert getestete Funktion (Cosine-Sort korrekt, leere/teilbesetzte
      Kandidatenmenge robust).
- [ ] `like_asset_id`-Suche liefert DINOv2-re-gerankte Top-`k`, wenn Rerank aktiv **und** Query-DINOv2-Vektor vorhanden.
- [ ] **Degradation lückenlos:** je Fallback-Bedingung (Modell aus / Setting aus / Text-Query / fehlende Vektoren)
      kommt das reine SigLIP2-Ergebnis ohne Fehler zurück. Je Zweig ein Test.
- [ ] Settings `rerank.enabled` (true) + `rerank.candidatePoolSize` (100) gelesen und wirksam; über die Einstellungen-UI
      einstellbar.
- [ ] Falls P36s `by-image`-Endpoint existiert: derselbe Rerank greift dort mit dem on-the-fly DINOv2-Vektor des
      Upload-Bilds. Falls P36 fehlt: als FINDINGS-Follow-up notiert, `like_asset_id`-Pfad reicht für diese Phase.
- [ ] `ruff check .` grün; Tests grün.

## Doc-Updates
- [ ] `docs/decisions/024-two-stage-rerank.md` — Ablauf, Pool-Größe, Fallback-Matrix ausführen.
- [ ] `docs/routes.md` / `docs/code-map.md` — Rerank-Funktion + Such-Pfad ergänzen.

## Report-Back
