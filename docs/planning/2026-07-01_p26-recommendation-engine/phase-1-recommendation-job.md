# Phase 1 — Recommendation-Job + Reason-Chain (Backend)

**Komplexität:** heikel (Scoring-Gewichtung + Reason-Chain sind der Denk-Kern) · **Status:** complete

## Kontext
- README → Kontrakt + Risiken (Scoring, Performance)
- Bestand lesen: `db/vector_index.py` (CLIP-Nachbarn), `inference/adapters/clip.py`, `api/search.py`, `jobs/queue.py`, `db/models.py`+Alembic
- **P22** (Relationships/Graph, Service, media_links) · Konzept Dok 050 §6, Dok 030 §5

## AK
- [x] Migration `recommendation_cache` (Kontrakt-Felder); up/down grün (0036, Kette + downgrade/upgrade getestet).
- [x] `RecommendationJob(source_asset_id)` erzeugt Empfehlungen aus **zwei** Quellen: CLIP-Nachbarn + graph-verbundene Assets (gleiche Person/Rolle/Film). Score = gewichtete Kombination (Gewichte aus settings).
- [x] Jede Empfehlung trägt Reason-Chain mit konkreten Signalen ({signal:"clip", detail:"0.94"}, {signal:"same_role", detail:"Tony Stark"}).
- [x] `GET /api/recommendations?asset_id=` aus Cache; fehlt → Job planen + leere Liste + `status:"computing"` (API rechnet nie synchron).
- [x] `GET .../{source}/{target}/why-not` erklärt fehlende/unterschwellige Signale (anwesende + fehlende + Schwelle).
- [x] Idempotent (voller Cache-Ersatz je Quelle); unter `min_score` nichts empfohlen. **Depth-Schutz entfällt** (Sackgassen-Job, löst keine Folge-Jobs aus — kein Rekursionspfad, `jobs.maxDepth` nicht nötig; siehe Deviation unten).

## Umsetzung
- [x] `db/models.py` (`Recommendation`) + Migration `recommendation_cache` (0036)
- [x] `jobs/recommendation_job.py` + `JobKind.RECOMMENDATION` in `queue.py` (**ein** Job statt `RecommendationJob` + `RecommendationUpdateJob` — s. Deviation)
- [x] Scoring-Modul: `recommendation/context.py` (Graph-Kontext, gebündelt) + `recommendation/scoring.py` (CLIP-Nachbarn + Graph → gewichteter Score → Reason-Chain)
- [x] `api/recommendations.py` + Registrierung in `main.py` + Pydantic-Schemas (Reason-Chain = geteilte Explainability-Struktur mit P25)
- [x] settings-Keys `recommendations.*` (`enabled`, `max_results`, `min_score`, `weights.{same_person,same_role,same_film,clip_similarity}`)
- [x] Doc: `docs/routes.md`, `docs/models.md`, `docs/code-map.md`, **ADR-026** (nicht 012 — war belegt)
- [x] Tests: `test_recommendation_scoring.py`, `test_recommendation_job.py`, `test_recommendation_api.py` (14, grün)

## Deviations (Phase 1)
- **Ein Job statt zwei:** Der Kontrakt reservierte `RecommendationUpdateJob` separat. Der idempotente
  `RecommendationJob` (rechnet neu + ersetzt Cache) bedient „auf Abruf berechnen" **und** „nach
  Graph-Änderung auffrischen" — ein zweiter, verhaltensgleicher Job wäre Rauschen. Auto-Trigger bei
  Graph-Änderungen sind spätere Integration (nicht Phase-1-Scope). Festgehalten in ADR-026.
- **ADR-Nummer 026 statt 012:** 012 war schon belegt (Galerie-Stapel), wie bei P24 (011 belegt).
- **Depth-Schutz weggelassen:** Der Job ist eine Sackgasse (keine Folge-Jobs) — es gibt keinen
  Rekursionspfad, den `jobs.maxDepth` schützen müsste. Kein solches Setting existiert im Projekt.
- **Signal-Semantik (belegt in Tests):** Zwei Fotos derselben Figur im selben Film teilen korrekt
  **alle drei** Graph-Signale (Person + Rolle + Film), nicht nur Person+Rolle — „Rolle" = direkte
  Verknüpfung, „Film" = deren 1-Hop-Ziel. Für Phase 2 (Karten) relevant: eine Karte kann mehrere
  Signal-Häkchen tragen.
