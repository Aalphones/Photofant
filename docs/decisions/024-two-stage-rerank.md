# ADR-024 — Two-Stage Retrieval & Rerank-Naht

**Status:** Angenommen (Naht-Prinzip; Rerank-Details folgen in P37 Phase 3)
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
2. **Stage 2 (Rerank):** eine **eigene, testbare Funktion** `rerank_by_appearance(query_dino_vec,
   candidate_asset_ids)` lädt die vorberechneten DINOv2-Vektoren der Kandidaten und sortiert sie nach
   Cosine-Ähnlichkeit zum Query. Kein Umbau der KNN-Schicht.

**Aktivierung/Degradation:**

- Global per Setting `rerank.enabled` (Default **true**) an/abschaltbar.
- Rerank greift **nur** bei vorhandenem Query-Bild. Fehlt das DINOv2-Modell (nicht aktiviert),
  ist `rerank.enabled=false`, oder ist die Query reiner Text → sauberer Fallback auf das reine
  SigLIP2-Ergebnis, **nie** ein Crash. Fähigkeits-Check statt blindem Aufruf; jeder Zweig wird
  in Phase 3 explizit getestet.

**Duplikat-Scan:** wird auf DINOv2 als Primär-Signal umgestellt (visuelle Erscheinung = was ein
Duplikat ausmacht). Der alte `dupe_clip_threshold` bleibt als Settings-Key inert für Rollback; der
neue `dupe_dino_threshold` wird in Phase 4 an realem Set kalibriert.

## Konsequenzen

- Die zwei Vektorräume bleiben getrennt (`vec_asset_embedding` 1024-dim SigLIP2, `vec_asset_dino`
  768-dim DINOv2) — kein gemeinsamer Index, keine Dimension-Kollision.
- Rerank ist als reine Funktion neben der Suche isoliert testbar; die Degradationspfade sind
  explizit statt implizit.
- Query-Zeit-Aufschlag ist vernachlässigbar (ein Query-Embed + ~100 Skalarprodukte).
- **Offen für Phase 3:** die konkrete Verdrahtung in die Bild→Bild-Endpoints und die Robustheit
  gegen „P36-Endpoints noch nicht/anders da" (siehe Plan-README, Abhängigkeit P36).
