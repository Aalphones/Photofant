# P7 · Phase 2 — Clustering & Auto-Zuordnung

> Rating: **heikel** (Cluster-Qualität entscheidet über die UX des ganzen Features; Schwellen-Kalibrierung) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Schwellen)
- [Konzept](../../Konzept-Photofant.md) §7 (HDBSCAN, Cosine-Matching, fixed_person-Ausnahme)
- Vektor-Index aus P5 Phase 4 (Face-Embeddings dort zusätzlich indizieren)

## Akzeptanzkriterien

- Initial-Clustering (HDBSCAN über alle Face-Embeddings) als manuell anstoßbarer Job → erzeugt Personen-Kandidaten; inkrementell: neues Face wird per Cosine gegen bestehende Personen gematcht (Score-Bänder aus dem Kontrakt: auto / Review / unknown).
- `fixed_person`-Instanzen werden nie automatisch umverteilt (§7).
- Face-Embeddings im Vektor-Index → `GET /api/faces/{id}/matches` (Top 10 disjunkte Personen, bester Treffer je Person).
- Cluster-Parameter (min_cluster_size etc.) in `app_config`; Kalibrierungs-Notizen in FINDINGS.

## Checkliste

- [ ] hdbscan-Dependency (Windows-Wheel prüfen; Fallback sklearn-DBSCAN dokumentieren)
- [ ] Initial-Clustering-Job + inkrementelles Matching im Import-Fluss
- [ ] Face-Embeddings in den Vektor-Index + matches-Endpoint
- [ ] Score-Band-Logik (auto/review/unknown) mit Config-Schwellen
- [ ] Tests: Matching-Bänder mit synthetischen Embeddings (deterministisch)
- [ ] Doc-Update: routes.md

## Report-Back
