# Phase 1 — Recommendation-Job + Reason-Chain (Backend)

**Komplexität:** heikel (Scoring-Gewichtung + Reason-Chain sind der Denk-Kern) · **Status:** pending

## Kontext
- README → Kontrakt + Risiken (Scoring, Performance)
- Bestand lesen: `db/vector_index.py` (CLIP-Nachbarn), `inference/adapters/clip.py`, `api/search.py`, `jobs/queue.py`, `db/models.py`+Alembic
- **P22** (Relationships/Graph, Service, media_links) · Konzept Dok 050 §6, Dok 030 §5

## AK
- [ ] Migration `recommendation_cache` (Kontrakt-Felder); up/down grün.
- [ ] `RecommendationJob(source_asset_id)` erzeugt Empfehlungen aus **zwei** Quellen: CLIP-Nachbarn + graph-verbundene Assets (gleiche Person/Rolle/Film). Score = gewichtete Kombination (Gewichte aus settings).
- [ ] Jede Empfehlung trägt Reason-Chain mit konkreten Signalen ({signal:"clip", detail:"0.94"}, {signal:"same_role", detail:"Tony Stark"}).
- [ ] `GET /api/recommendations?asset_id=` aus Cache; fehlt → Job planen + leere Liste + „wird berechnet" (API rechnet nie synchron).
- [ ] `GET .../{source}/{target}/why-not` erklärt fehlende/unterschwellige Signale.
- [ ] Idempotent, Depth-Schutz (`jobs.maxDepth`); unter `minScore` nichts empfohlen.

## Umsetzung
- [ ] `db/models.py` + Migration `recommendation_cache`
- [ ] `jobs/recommendation_job.py` (+ `RecommendationUpdateJob`) + Registrierung in `queue.py`
- [ ] Scoring-Modul: Kandidaten (CLIP-Vorfilter) → Graph-Signale → gewichteter Score → Reason-Chain
- [ ] `api/recommendations.py` + Registrierung + Pydantic-Schemas (inkl. Explainability-Payload, geteilt mit P25)
- [ ] settings-Keys `recommendations.*`
- [ ] Doc: `docs/routes.md`, `docs/models.md`, `docs/code-map.md`, ADR-012
