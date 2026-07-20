# ADR-030 — Empfehlungs-Cache: gezielte Invalidierung statt TTL/Rebuild-Button

**Status:** Angenommen — Phase 1 umgesetzt (Utilities), Phasen 2-4 verdrahten die Call-Sites
**Datum:** 2026-07-20
**Betrifft:** Plan `2026-07-20_recommendation-cache-invalidation`, löst den „später"-Punkt aus
ADR-026 (`recommendation_job.py:12-13`) ein.

## Kontext

`recommendation_cache` (ADR-026) wird nur bei Cache-Fehltreffer berechnet und bleibt danach
stehen. `score_pair()` hängt vom Wissensgraph-Kontext **beider** Seiten eines Paares ab —
ändert sich Personen-/Rollen-/Film-Zugehörigkeit (neue Zuordnung, verknüpfte Rolle, geänderte
Beziehung), sind gecachte Zeilen für jedes betroffene Asset falsch, ohne dass irgendwo ein Job
sichtbar würde.

## Optionen

- **TTL (Cache läuft nach X ab):** verworfen — falsche Empfehlungen bleiben bis zu TTL sichtbar,
  und die meisten Graph-Änderungen sind selten genug, dass ein kurzes TTL nur unnötig oft neu
  rechnet, ein langes TTL das Kernproblem kaum verkürzt.
- **Manueller Rebuild-Button:** verworfen — verlagert das Problem zum User, der nicht wissen
  kann, wann sein Cache stale ist; still falsche Empfehlungen sind schlechter als ein sichtbarer
  Recompute-Job.
- **Gezielte Invalidierung bei der auslösenden Mutation (gewählt).**

## Entscheidung

Jede Mutation, die den Graph-Kontext eines Assets ändert (manuelle Face-/Person-Zuweisung,
Wissensgraph-Verknüpfung, Clustering-Zuordnung), löscht **vor ihrem Commit** die betroffenen
`recommendation_cache`-Zeilen — trifft die Ursache statt nur das Symptom, kein neuer
Wartungs-Screen-Eintrag nötig.

- `assets_of_persons`/`assets_for_entity` (`recommendation/context.py`) ermitteln, welche
  Assets von einer Entity-/Personen-Änderung betroffen sind.
- `invalidate_recommendations(session, asset_ids)` (`jobs/recommendation_job.py`) löscht
  Cache-Zeilen, die eines der Assets **als Quelle oder als Ziel** referenzieren — eine Zeile
  ist schon stale, wenn nur die Kandidaten-Seite sich ändert, nicht nur die Quelle.
- Die Invalidierung lebt **immer im Aufrufer** (API-Route/Job), nie in `knowledge/service.py` —
  das Modul bleibt bewusst frei von Person-/Asset-Imports (Architektur-Grenze aus P22).
- Nach der Löschung liefert `GET /recommendations?asset_id=` beim nächsten Aufruf
  `status=computing` und plant `RecommendationJob` neu — kein zusätzlicher Job-Typ.

## Konsequenzen

- Empfehlungen sind nach einer Graph-Änderung spätestens beim nächsten Abruf des betroffenen
  Assets korrekt, nicht erst nach TTL-Ablauf oder manuellem Eingriff.
- Jede Call-Site (Phasen 2-4) muss die Invalidierung selbst aufrufen — vergisst eine künftige
  neue Mutation das, ist der Cache wieder lautlos stale. Kein zentraler Hook fängt das ab
  (Kehrseite der Architektur-Grenze); Tests pro Call-Site sind der Schutz.
- `recommendation_cache.recommended_asset_id` bekommt einen Index (`ix_recommendation_target`,
  Migration 0039) — die neue Filterung auf dieser Spalte wäre sonst ein Full-Table-Scan.
