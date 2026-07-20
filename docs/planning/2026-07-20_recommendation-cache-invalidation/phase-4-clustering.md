# Phase 4 — Clustering (automatische Personen-Zuordnung)

Voraussetzung: Phase 1 (Utilities) committed. Dies ist der vermutliche Hauptverursacher der
gemeldeten falschen Empfehlungen — die meisten Personen-Zuordnungen laufen automatisch über
Clustering (nach jedem Import), nicht über die manuellen Aktionen aus Phase 2. Vor diesem Plan
hatte dieser Pfad **keinen einzigen** Invalidierungs-Hook (weder für Empfehlungen noch für
Smart-Alben) — anders als Phase 2/3 gibt es hier kein bestehendes Muster zum 1:1-Kopieren,
deshalb `standard`-Rating statt `mechanisch`.

## Kontext (lesen vor dem Start)

- `backend/photofant/jobs/recommendation_job.py` — `invalidate_recommendations` (Phase 1).
- `backend/photofant/clustering/engine.py` — `run_initial_clustering` (Zeile ~94-265). Zwei
  Stellen ändern `face.person_id`:
  - Pre-Match-Stage (Zeile ~154-158): `result = match_face_incremental(...)`; bei
    `result.band == "auto"` wird `face.person_id = result.person_id` gesetzt.
  - HDBSCAN-Zuweisung (Zeile ~246-248): Schleife über `faces_from_unknown`, setzt
    `face.person_id = person.id` für neu erzeugte Personen.
  Committet einmal am Ende bei `session.commit()` (Zeile ~253).
- `backend/photofant/jobs/clustering_job.py` — `run_incremental_match` (Zeile ~49-109): läuft
  automatisch nach jedem Face-Import für ein einzelnes Face. Setzt `face.person_id =
  result.person_id` bei `result.band == "auto"` (Zeile ~64-65), committet bei Zeile ~109.

## AK dieser Phase

1. **`clustering/engine.py::run_initial_clustering`** — ein `set[int]` `changed_face_ids`
   sammelt während der Funktion jede `face.id`, deren `person_id` sich ändert:
   - Im Pre-Match-Zweig (nach Zeile ~157, `face.person_id = result.person_id`):
     `changed_face_ids.add(face_id)`.
   - Im HDBSCAN-Zweig (in der Schleife um Zeile ~246-248, `face.person_id = person.id`):
     `changed_face_ids.add(face.id)`.

   Direkt **vor** `session.commit()` (Zeile ~253):
   ```python
   if changed_face_ids:
       from photofant.jobs.recommendation_job import invalidate_recommendations

       affected_assets = {
           int(row[0])
           for row in session.execute(
               select(Face.asset_id)
               .where(Face.id.in_(changed_face_ids), Face.asset_id.isnot(None))
           ).all()
       }
       invalidate_recommendations(session, affected_assets)
   ```
   (`select`/`Face` sind in dieser Datei bereits importiert — prüfen und ggf. den bestehenden
   Import wiederverwenden statt zu duplizieren.)

2. **`clustering_job.py::run_incremental_match`** — nur der `auto`-Zweig ändert `person_id`
   (Zeile ~64-65); der `review`-Zweig legt nur ein `ReviewItem` an, keine Invalidierung nötig.
   Direkt nach `face.person_id = result.person_id; session.flush()` (Zeile ~65-66), **vor**
   `session.commit()` (Zeile ~109):
   ```python
   if face.asset_id is not None:
       from photofant.jobs.recommendation_job import invalidate_recommendations
       invalidate_recommendations(session, [face.asset_id])
   ```
   Platzierung: kann direkt nach Zeile 66 stehen (vor den `materialize_assignment`-Aufrufen)
   oder erst kurz vor Zeile 109 — beides ist vor demselben Commit, Reihenfolge ist egal.
   Nicht in den `elif result.band == "review"`-Zweig einbauen (dort ändert sich `person_id`
   nicht).

## Tests

**Es gibt noch keine Testdatei für `clustering/engine.py` oder `clustering_job.py`** (geprüft:
kein `test_clustering*.py` in `backend/tests/`) — hier ist nichts zum Abschauen, die Tests unten
sind self-contained beschrieben.

`match_face_incremental` liefert ein `MatchResult(person_id: int | None, score: float, band:
str)` (`clustering/engine.py` Zeile ~22-26) — mit `monkeypatch.setattr` auf das Modul-Attribut
ersetzen (`monkeypatch.setattr("photofant.clustering.engine.match_face_incremental", ...)` bzw.
für `clustering_job.py` auf `photofant.clustering.engine.match_face_incremental`, da die Funktion
dort per `from photofant.clustering.engine import match_face_incremental` importiert wird —
patchen, wo sie **benutzt** wird).

Neue Datei `backend/tests/test_recommendation_invalidation_clustering.py`:

- `test_run_initial_clustering_pre_match_invalidates_recommendations` — Setup: eine `_unknown`-
  Person (`Person(is_unknown=True)`), ein `Face` mit `person_id=<unknown>.id` und einem
  Dummy-`embedding` (z. B. `np.zeros(512, dtype=np.float32).tobytes()` — Dimension egal, wird
  nur für `_run_hdbscan` gebraucht, nicht für den Pre-Match-Zweig selbst), `Face.asset_id` auf
  ein existierendes Asset gesetzt. `monkeypatch.setattr(engine, "match_face_incremental", lambda
  session, face_id: MatchResult(person_id=<eine echte Ziel-Person-id>, score=0.9, band="auto"))`.
  Cache-Zeile (`Recommendation`) für das Asset vorab anlegen. `run_initial_clustering(session)`
  aufrufen (HDBSCAN-Zweig läuft mit nur einem Embedding leer durch, das ist ok — der Pre-Match
  passiert vorher). Cache-Zeile ist danach weg.
- `test_run_initial_clustering_hdbscan_invalidates_recommendations` — statt echtes HDBSCAN zu
  triggern (aufwendig, braucht genug nah beieinanderliegende Embeddings), stattdessen
  `monkeypatch.setattr(engine, "_run_hdbscan", lambda embeddings, min_cluster_size, epsilon:
  np.array([0, 0]))` — zwei Faces landen deterministisch in Cluster `0`. Zwei `_unknown`-Faces
  mit `asset_id` auf zwei verschiedene existierende Assets anlegen, `match_face_incremental`
  mocken auf `band="unknown"` (damit der Pre-Match-Zweig nichts tut und die Faces für HDBSCAN
  übrig bleiben). Cache-Zeile für eines der beiden Assets vorab anlegen. Nach dem Lauf: Zeile
  weg (die Faces wurden einer neu erzeugten Person zugewiesen).
- `test_run_incremental_match_auto_invalidates_recommendations` — `Face` mit `asset_id` und
  `person_id=<unknown>`; `monkeypatch.setattr("photofant.jobs.clustering_job.
  match_face_incremental", lambda session, face_id: MatchResult(person_id=<ziel>, score=0.9,
  band="auto"))`. `materialize_assignment`/`move_face_crops_to_person` ebenfalls monkeypatchen
  (No-ops), da sie Dateisystem-Operationen anstoßen, die in diesem Test nicht gebraucht werden.
  Cache-Zeile für das Face-Asset vorab anlegen. `run_incremental_match(face_id)` aufrufen →
  Zeile weg.
- `test_run_incremental_match_review_does_not_invalidate` — gleiches Setup, aber
  `band="review"` → Cache-Zeile bleibt unverändert (negativer Test: kein Person-Wechsel, keine
  Invalidierung nötig).

## Doc-Updates

Keine zusätzlichen — Phase 1 deckt `code-map.md`/ADR ab.

## Report-Back
