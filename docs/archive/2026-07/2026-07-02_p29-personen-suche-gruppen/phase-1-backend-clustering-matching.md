# Phase 1 — Backend: Clustering matcht erst gegen bestehende Personen

**Tier:** standard
**Status:** complete

---

## Kontext (vorher lesen)

- `backend/photofant/clustering/engine.py` — `run_initial_clustering` (Zeile 81-193), `match_face_incremental` (Zeile 38-78)
- `backend/photofant/jobs/clustering_job.py` — `run_incremental_match` (Zeile 49-110), Vorlage für Auto-Assign- und Review-Handling
- `backend/photofant/db/face_vector_index.py` — `search_disjoint_persons` (Zeile 94-124, gibt bestes Face pro Person zurück)
- `backend/photofant/media/person_folders.py` — `materialize_clustering_results` (Zeile 412-452): läuft **nach** `run_initial_clustering` bereits über **alle** `(asset_id, person_id)`-Paare mit `person_id != unknown` ohne bestehende Instanz — Materialisierung für die neuen Auto-Matches braucht daher **keinen** zusätzlichen Aufruf in dieser Phase, sie läuft automatisch mit.

---

## Abnahme-Kriterien

- [x] Ein noch-unbekanntes Gesicht mit Score ≥ `face_auto_threshold` gegen eine bestehende Person wird dieser Person zugewiesen (`face.person_id` gesetzt), **bevor** HDBSCAN läuft
- [x] Ordner/Instanz für den Auto-Match wird materialisiert (läuft automatisch über den bestehenden `materialize_clustering_results`-Call in `_run_initial_clustering`)
- [x] Ein Gesicht mit Score zwischen `face_review_threshold` und `face_auto_threshold` erzeugt einen `ReviewItem` (`type="face_suggestion"`), bleibt aber bei „Unbekannt" — kein Duplikat, wenn schon ein offener Review-Eintrag für dieses Gesicht existiert
- [x] Ein Gesicht ohne Match (< `face_review_threshold`) bleibt unverändert Kandidat für HDBSCAN
- [x] Gesichter mit `fixed_person` (über `AssetInstance.fixed_person`) werden von der Matching-Vorstufe **nicht** angefasst (wie bisher schon bei HDBSCAN ausgenommen)
- [x] `run_initial_clustering` gibt zusätzlich `matched_auto` und `matched_review` in den Stats zurück
- [x] Bestehende Abnahme „Bereits benannten/zugewiesenen Gesichtern passiert beim Clustering nichts" bleibt erfüllt — die Matching-Vorstufe rührt ausschließlich Gesichter mit `person_id == unknown_person_id`

---

## Checkliste

### clustering/engine.py — `run_initial_clustering` umbauen

- [x] `unknown_person` / `unknown_person_id` und `fixed_face_ids`-Berechnung (aktuell Zeile 131-145) **vor** die HDBSCAN-Vorbereitung ziehen — wird jetzt auch von der neuen Matching-Vorstufe gebraucht
- [x] Neue Vorstufe **vor** dem HDBSCAN-Aufruf einfügen: für jedes `face_id` aus `face_ids` (die bereits geladenen Embeddings), das aktuell `person_id == unknown_person_id` und **nicht** in `fixed_face_ids` ist:
  ```python
  from photofant.clustering.engine import match_face_incremental  # bereits im Modul
  from photofant.db.models import ReviewItem
  from datetime import UTC, datetime

  matched_auto = 0
  matched_review = 0

  for face_id in face_ids:
      if face_id in fixed_face_ids:
          continue
      face = session.get(Face, face_id)
      if face is None or face.person_id != unknown_person_id:
          continue

      result = match_face_incremental(session, face_id)

      if result.band == "auto" and result.person_id is not None:
          face.person_id = result.person_id
          matched_auto += 1
          log.info("Face %d pre-matched (auto) to person %d (score=%.3f)", face_id, result.person_id, result.score)

      elif result.band == "review" and result.person_id is not None:
          existing = session.query(ReviewItem).filter(
              ReviewItem.type == "face_suggestion",
              ReviewItem.face_id == face_id,
              ReviewItem.resolved_at.is_(None),
          ).first()
          if existing is None:
              asset_id = face.asset_id or 0
              session.add(ReviewItem(
                  type="face_suggestion",
                  asset_a_id=asset_id,
                  asset_b_id=asset_id,
                  phash_distance=0,
                  face_id=face_id,
                  suggested_person_id=result.person_id,
                  score=result.score,
                  created_at=datetime.now(UTC).replace(tzinfo=None),
              ))
          matched_review += 1

  session.flush()
  ```
  🟡 **Wichtig:** kein `session.commit()` hier — die Funktion committet weiterhin genau einmal am Ende (Zeile 184 im alten Stand). Ein Zwischen-Commit würde die spätere HDBSCAN-Transaktion unnötig aufspalten.
- [x] HDBSCAN läuft danach unverändert über **alle** geladenen Embeddings (auch die gerade gematchten) — kein Filtern der `embeddings`/`face_ids`-Arrays nötig. Die bestehende Prüfung `face.person_id == unknown_person_id` in der Cluster-Zuweisungsschleife (aktuell Zeile 166) schließt die gerade zugewiesenen Gesichter automatisch aus, weil ihr `person_id` nicht mehr `unknown_person_id` ist.
- [x] `fixed_face_ids`-Berechnung nicht doppelt ausführen — beim Hochziehen die alte Stelle (Zeile 134-145) entfernen, nicht kopieren
- [x] Rückgabe-Dict um `matched_auto`, `matched_review` erweitern:
  ```python
  return {
      "persons_created": persons_created,
      "faces_assigned": faces_assigned,
      "noise_count": noise_count,
      "matched_auto": matched_auto,
      "matched_review": matched_review,
  }
  ```

### Sanity-Check

- [x] Bei leerem `rows` (keine Embeddings) — early return (Zeile 95-97) bleibt vor der neuen Vorstufe, keine Änderung nötig
- [ ] Manuell: Person A existiert, neues unbekanntes Gesicht liegt klar über `face_auto_threshold` zu Person A → nach `POST /api/clustering/run` ist das Gesicht bei Person A, kein neuer Person-Bucket entstanden (Teil der Plan-End-Smoke-Checkliste)
- [ ] Manuell: Score liegt im Review-Band → Gesicht bleibt „Unbekannt", taucht in der bestehenden Review-Queue auf (Teil der Plan-End-Smoke-Checkliste)

---

## Doc-Updates

- [x] `docs/code-map.md` — `clustering/engine.py` steht bereits im „Personen & Faces"-Eintrag (Ordner-Ebene), keine Struktur-Änderung in dieser Phase → kein Update nötig
