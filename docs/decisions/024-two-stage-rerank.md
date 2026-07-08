# ADR-024 — Two-Stage Retrieval & Rerank-Naht

**Status:** Angenommen — vollständig umgesetzt (P37 Phase 3: Bild→Bild-Rerank; Phase 4: Duplikat-Scan auf DINOv2)
**Datum:** 2026-07-08
**Betrifft:** Plan `2026-07-07_p37-dinov2-reranking`, baut auf ADR-023 (DINOv2 als visueller Re-Ranker) und ADR-022 (Embedder-Naht) auf

---

## Kontext

DINOv2 (ADR-023) liefert ein rein visuelles Ähnlichkeitssignal, greift aber nur, wenn ein
**Query-Bild** existiert. Die Bild→Bild-Pfade (`like_asset_id`, `POST /api/search/by-image`) und
der Duplikat-Scan haben so einen Anker; die Text-Semantiksuche hat keinen und bleibt reines SigLIP2.

Die Frage ist, **wie** DINOv2 an die Suche andockt, ohne die bestehende KNN-Schicht (SigLIP2) umzubauen.

## Optionen

- **Direkt einen DINOv2-KNN-Index über die ganze Bibliothek abfragen:** verworfen — würde die
  SigLIP2-Retrieval-Schicht duplizieren und die beiden Vektorräume vermischen. DINOv2 ist für
  *Re-Ranking einer kleinen Kandidatenmenge* gedacht, nicht als primäres Retrieval.
- **Rerank in die KNN-Schicht einweben:** verworfen — koppelt die zwei Modelle, macht die
  Degradation (Text-Query / Modell fehlt) schwer isoliert testbar.
- **Two-Stage: SigLIP2-KNN als Kandidaten-Pool → DINOv2-Cosine-Rerank als eigene Funktion (gewählt).**

## Entscheidung

**Retrieve-then-rerank in zwei Stufen:**

1. **Stage 1 (Retrieval):** SigLIP2-KNN liefert Top-N Kandidaten (`rerank.candidatePoolSize`, Default 100).
2. **Stage 2 (Rerank):** eine **eigene, testbare Funktion** `rerank_by_appearance(session,
   query_dino_vec, candidate_asset_ids, top_k)` (`photofant/search/rerank.py`) lädt die vorberechneten
   DINOv2-Vektoren der Kandidaten (`vector_index.load_dino_embeddings`) und sortiert sie nach
   Cosine-Ähnlichkeit zum Query. Der reine Sortier-Kern (`_rank_by_cosine`) ist DB-frei und isoliert
   getestet. Kein Umbau der KNN-Schicht.

**Aktivierung/Degradation:**

- Global per Setting `rerank.enabled` (Default **true**) an/abschaltbar.
- Rerank greift **nur** bei vorhandenem Query-Bild. Fehlt das DINOv2-Modell (nicht aktiviert),
  ist `rerank.enabled=false`, oder ist die Query reiner Text → sauberer Fallback auf das reine
  SigLIP2-Ergebnis, **nie** ein Crash. Fähigkeits-Check statt blindem Aufruf; jeder Zweig wird
  in Phase 3 explizit getestet.

**Duplikat-Scan:** auf DINOv2 als Primär-Signal umgestellt (visuelle Erscheinung = was ein Duplikat
ausmacht). Betrifft alle vier Stellen, die zuvor `clip_embedding` für Ähnlichkeitsvergleiche lasen:

- Post-Embedding-Check (`embedding_job._check_for_dupes`) — läuft nur, wenn ein DINOv2-Embedding
  vorliegt (Modell in der Modelle-UI aktiv); ohne DINOv2 findet **kein** automatischer Check mehr
  statt (bewusster Trade-off, kein Fallback auf SigLIP2 — Duplikat-Erkennung ist Primärsignal, kein
  Rerank mit Degradationspfad).
- Voll-/Selektions-Scan (`dupe_scan_job.run_dupe_scan_job`, „Duplikate scannen").
- Personen-Duplikatsuche (`api/duplicates.py`).
- Trainings-Set-Near-Dupe-Rate + Review (`collections/stats.py`, `api/collections.py` — eigene
  Entscheidung in Phase 4, da gleiche Fragestellung: visuelle Ähnlichkeit einer Trainings-Kollektion).

Ausdrücklich **nicht** umgestellt: `GET /assets/{id}/similar` (Lightbox/MCP „ähnliche Bilder") bleibt
auf SigLIP2 — andere Fragestellung (breite semantische Ähnlichkeit statt strenges Duplikat), eigener
Schwellwert `similar_clip_threshold`.

Die alten `dupe_clip_threshold`/`training_near_dupe_clip_threshold` bleiben als Settings-Keys inert
für Rollback. Neue Keys `dupe_dino_threshold` (Default 0.08 ≈ 92 % Ähnlichkeit) und
`training_near_dupe_dino_threshold` (Default 0.12 ≈ 88 %) sind **begründete Startwerte** — DINOv2s
Distanz-Regime unterscheidet sich von CLIP/SigLIP2 und wurde nicht 1:1 übernommen. Feinjustierung an
einem realen Set ist Smoke-Checkliste #2 (Nutzer-Aufgabe, kein Live-Test im Rahmen dieser Umsetzung).

## Konsequenzen

- Die zwei Vektorräume bleiben getrennt (`vec_asset_embedding` 1024-dim SigLIP2, `vec_asset_dino`
  768-dim DINOv2) — kein gemeinsamer Index, keine Dimension-Kollision.
- Rerank ist als reine Funktion neben der Suche isoliert testbar; die Degradationspfade sind
  explizit statt implizit.
- Query-Zeit-Aufschlag ist vernachlässigbar (ein Query-Embed + ~100 Skalarprodukte).

## Verdrahtung (Phase 3, umgesetzt)

Beide Bild→Bild-Pfade in `photofant/api/search.py` hängen den Rerank hinter Stage 1:

- **`like_asset_id` (`POST /api/search/semantic`):** Query-DINOv2-Vektor ist das gespeicherte
  `asset.dino_embedding` des Quell-Assets (kein Modell zur Suchzeit nötig).
- **Upload (`POST /api/search/by-image`):** Query-Vektor wird on-the-fly per
  `resolve_image_embedder(role="visual_rerank")` aus dem Upload embedded; ist kein DINOv2-Modell
  aktiv, liefert das `None` → Fallback.

Der aktive, soft-delete-gefilterte Kandidaten-Pool wird re-gerankt (`_rerank_pool`): Kandidaten **mit**
DINOv2-Vektor zuerst nach Erscheinung, Kandidaten **ohne** Vektor in SigLIP2-Reihenfolge hinten
angehängt — das Ergebnis schrumpft nie. Beim Upload gilt der SigLIP-`min_score`-Floor **vor** dem
Rerank (er ist eine SigLIP-Raum-Schwelle). Fallback-Matrix (jeder Zweig getestet):

| Bedingung | Verhalten |
|---|---|
| `rerank.enabled = false` | reines SigLIP2 |
| Text-Query (`query`) | reines SigLIP2 (DINOv2 kann keinen Text) |
| Quell-Asset ohne `dino_embedding` (like) | reines SigLIP2 |
| kein DINOv2-Modell aktiv (Upload) | reines SigLIP2 |
| Kandidat ohne DINOv2-Vektor | in SigLIP2-Reihenfolge hinten angehängt |
