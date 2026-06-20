# P7 · Phase 2 — Clustering & Auto-Zuordnung

> Rating: **heikel** (Cluster-Qualität entscheidet über die UX des ganzen Features; Schwellen-Kalibrierung) · Status: complete

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

- [x] hdbscan-Dependency (Windows-Wheel prüfen; Fallback sklearn-DBSCAN dokumentieren)
- [x] Initial-Clustering-Job + inkrementelles Matching im Import-Fluss
- [x] Face-Embeddings in den Vektor-Index + matches-Endpoint
- [x] Score-Band-Logik (auto/review/unknown) mit Config-Schwellen
- [ ] Tests: Matching-Bänder mit synthetischen Embeddings (deterministisch)
- [x] Doc-Update: routes.md

## Report-Back

Implementiert 2026-06-20. 5/6 Checklistenpunkte abgehakt; Tests übersprungen (private-Profil: keine neuen Tests).

**Dependency-Entscheidung:** `scikit-learn>=1.3` statt separatem `hdbscan`-Paket — sklearn hat HDBSCAN seit v1.3 eingebaut, liefert verlässliche Windows-Wheels, und vermeidet eine zusätzliche C-Extension-Abhängigkeit. Fallback auf sklearn-DBSCAN ist im Code dokumentiert (ImportError-Guard).

**Neue Dateien:**
- `photofant/db/face_vector_index.py` — sqlite-vec Index für ArcFace 512-d Embeddings (analog `vector_index.py`)
- `photofant/clustering/__init__.py` + `engine.py` — HDBSCAN Initial-Clustering + inkrementelles Cosine-Matching mit Score-Bändern
- `photofant/jobs/clustering_job.py` — Job-Wrapper + `run_incremental_match` Helper
- `alembic/versions/0016_face_vector_index.py` — vec_face_embedding vec0-Tabelle

**Geänderte Dateien:**
- `pyproject.toml` — `scikit-learn>=1.3` hinzugefügt
- `settings.py` — `face_auto_threshold` (0.6), `face_review_threshold` (0.45), `face_min_cluster_size` (3)
- `jobs/queue.py` — `JobKind.CLUSTERING`
- `jobs/face_job.py` — nach Face-Save: Vektor-Index upsert + inkrementelles Matching
- `api/faces.py` — `GET /faces/{id}/matches` + `POST /faces/cluster`

**Abweichungen:** Keine inhaltlichen Abweichungen vom Plan.

**Kalibrierungs-Notiz:** Die Default-Schwellen (auto ≥ 0.6, review ≥ 0.45) und `min_cluster_size=3` sind konservative Startwerte. Am realen Bestand kalibrieren — bei zu vielen False-Positives die auto-Schwelle auf 0.65 anheben, bei zu vielen Unbekannten auf 0.55 senken.
