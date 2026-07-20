# Phase 2 — Manuelle Face-/Person-Aktionen

Voraussetzung: Phase 1 committed (`invalidate_recommendations` und `assets_of_persons` stehen
bereit). Jede Stelle hier folgt demselben Muster wie das bestehende
`enqueue_reevaluate_assets(asset_ids)` (Smart-Alben-Invalidierung) an derselben Zeile — nur
synchron statt als Job (reines `DELETE`, keine teure Neuberechnung).

**Import-Konvention:** In allen betroffenen Dateien werden Cross-Modul-Imports lokal innerhalb
der Funktion gemacht, nicht auf Modul-Ebene (bestehendes Muster — siehe z. B. den lokalen
`from photofant.jobs.collections_job import enqueue_reevaluate_assets` in genau diesen
Funktionen). An jeder Stelle unten also `from photofant.jobs.recommendation_job import
invalidate_recommendations` lokal ergänzen, direkt vor der ersten Verwendung im selben Stil.

## Kontext (lesen vor dem Start)

- `backend/photofant/jobs/recommendation_job.py` — `invalidate_recommendations` (Phase 1).
- `backend/photofant/api/faces.py` — `delete_face` (Zeile ~450-492), `assign_face`
  (Zeile ~504-547).
- `backend/photofant/api/assets.py` — `assign_person_to_asset` (Zeile ~1343-1381).
- `backend/photofant/api/persons.py` — `merge_persons_endpoint` (Zeile ~362-399),
  `delete_person_endpoint` (Zeile ~402-435), `split_person` (Zeile ~518-542).
- `backend/photofant/media/person_folders.py` — `split_faces` (Zeile ~949-1054): berechnet
  `affected_assets` bereits lokal (Zeile ~997-1001), gibt sie aber **nicht** zurück.
- `backend/photofant/api/review_queue.py` — `resolve_face_review`, alle drei Zweige
  `confirm`/`reject`/`reassign` (Zeile ~100-220).
- `backend/photofant/jobs/bulk_assign_person_job.py` — `_assign_one_asset` (Zeile ~50-68).

## AK dieser Phase

Für jede Stelle: `invalidate_recommendations(session, [...])` wird **vor** dem jeweiligen
`session.commit()` aufgerufen, mit exakt den Asset-IDs, deren `person_id`/Zuordnung sich in
dieser Funktion ändert.

1. **`faces.py::delete_face`** — innerhalb des bestehenden `if asset_id is not None:`-Blocks
   (vor `prune_orphaned_instances` oder danach, beides korrekt — Hauptsache vor dem
   `session.commit()` in Zeile ~487), `invalidate_recommendations(session, [asset_id])`
   aufrufen.
2. **`faces.py::assign_face`** — nach dem `reassign_face`-Aufruf, **vor** `session.commit()`
   (Zeile ~535): `if result["asset_id"] is not None: invalidate_recommendations(session,
   [result["asset_id"]])`.
3. **`assets.py::assign_person_to_asset`** — vor `session.commit()` (Zeile ~1372):
   `invalidate_recommendations(session, [asset_id])`.
4. **`persons.py::merge_persons_endpoint`** — der Endpunkt committet bereits bei Zeile ~384 und
   berechnet `asset_ids` danach (Zeile ~386-391, Query auf `into_id`). Ergänzen: sobald
   `asset_ids` vorliegt, `invalidate_recommendations(session, asset_ids)` **plus ein weiteres**
   `session.commit()` (zweite kleine Transaktion, analog zum bestehenden Muster — der erste
   Commit deckt den physischen Move ab, der zweite die Cache-Invalidierung), **bevor**
   `enqueue_reevaluate_assets` gefeuert wird.
5. **`persons.py::delete_person_endpoint`** — analog: `asset_ids = result.pop("asset_ids", [])`
   liegt bei Zeile ~427 schon vor. Direkt danach `invalidate_recommendations(session,
   asset_ids)` + `session.commit()`, vor dem bestehenden `enqueue_reevaluate_assets`.
6. **`person_folders.py::split_faces`** — Rückgabe-Dict um `"asset_ids"` erweitern:
   - Early-Return bei `faces_moved == 0` (Zeile ~995): `{"new_person_id": None, "faces_moved":
     0, "instances_created": 0, "asset_ids": []}`.
   - Finaler Return (Zeile ~1050-1054): `"asset_ids": [int(row[0]) for row in
     affected_assets]` ergänzen (die Variable `affected_assets` aus Zeile ~997-1001 ist an
     dieser Stelle noch in Scope).
7. **`persons.py::split_person`** — nach `session.commit()` (Zeile ~537): `asset_ids =
   result.get("asset_ids", [])`, `if asset_ids: invalidate_recommendations(session, asset_ids);
   session.commit()`. **Bonus in derselben Änderung** (kostet nichts extra, da `asset_ids`
   jetzt vorliegt): direkt danach `from photofant.jobs.collections_job import
   enqueue_reevaluate_assets; asyncio.ensure_future(enqueue_reevaluate_assets(asset_ids))` —
   schließt die im README unter „Follow-ups" **nicht** gemeinte Lücke (die dort gemeinte Lücke
   ist `reject` in `review_queue.py`, die bleibt offen). Diese Smart-Alben-Ergänzung hier ist
   ein natürlicher Nebeneffekt, kein Scope-Creep — kein zusätzlicher Code-Pfad nötig.
8. **`review_queue.py::resolve_face_review`** — alle drei Zweige ändern `face.person_id`
   (`confirm`: direkt Zeile ~133; `reject`: über `reassign_face` Zeile ~183; `reassign`: über
   `reassign_face` Zeile ~205). In jedem Zweig **vor** dessen `session.commit()`:
   `if face.asset_id is not None: invalidate_recommendations(session, [face.asset_id])`.
   Nur die Recommendation-Invalidierung ergänzen — die Smart-Alben-Lücke im `reject`-Zweig
   bleibt bewusst offen (README „Follow-ups").
9. **`bulk_assign_person_job.py::_assign_one_asset`** — vor `session.commit()` (Zeile ~67):
   `invalidate_recommendations(session, [asset_id])`.

## Tests

Neue Datei `backend/tests/test_recommendation_invalidation_manual.py` (FastAPI-Testclient-Stil
wie `test_recommendation_api.py`, oder direkte Funktionsaufrufe wie `test_recommendation_job.py`
— je nachdem, was für die jeweilige Stelle weniger Mock-Aufwand bedeutet). Pro Stelle: Cache-Zeile
für das betroffene Asset vorab anlegen (`session.add(Recommendation(...))`), Mutation auslösen,
prüfen, dass die Zeile weg ist. Mindestens:

- `assign_face` invalidiert die Cache-Zeile des reassignten Assets.
- `merge_persons_endpoint` invalidiert Cache-Zeilen für alle Assets der Ziel-Person.
- `split_person` liefert jetzt `asset_ids` im Response-Dict **und** invalidiert deren Cache.
- `resolve_face_review` (`action="confirm"`) invalidiert die Cache-Zeile des Assets.
- Eine Zeile, bei der das betroffene Asset nur als **Ziel** (`recommended_asset_id`), nicht als
  Quelle in der Cache-Zeile auftaucht — muss trotzdem verschwinden (deckt den Kern-Fix aus
  Phase 1 im echten Aufrufkontext ab, nicht nur isoliert).

## Doc-Updates

Keine — Phase 1 hat `code-map.md` bereits aktualisiert, diese Phase ändert nur Call-Sites.

## Report-Back

**Status: complete.**

Alle 9 Call-Sites ergänzt (`faces.py::delete_face/assign_face`, `assets.py::assign_person_to_asset`,
`persons.py::merge_persons_endpoint/delete_person_endpoint/split_person`,
`person_folders.py::split_faces` um `asset_ids`, `review_queue.py::resolve_face_review` alle
3 Zweige, `bulk_assign_person_job.py::_assign_one_asset`).

**Abweichung vom Plan:** `split_faces` (Rückgabe) und `delete_person` hatten vorher lose
typisierte Dicts (`dict[str, int | None]` bzw. `dict[str, object]`). Die neue `asset_ids`-Zeile
hätte diese Union weiter aufgeweicht und neue mypy-Fehler an den Call-Sites erzeugt — stattdessen
`SplitFacesResult`/`DeletePersonResult` als `TypedDict` eingeführt (`person_folders.py`). Netto-Effekt:
5 vorbestehende mypy-Fehler an genau diesen Stellen sind mitverschwunden (32 → 27 Fehler in den
6 berührten Dateien, keiner davon neu).

Neue Testdatei `test_recommendation_invalidation_manual.py` (6 Tests) — ruft die Endpunkt-Funktionen
direkt auf (kein HTTP-Layer), physische Datei-Operationen laufen ohne echte Dateien defensiv durch
(bereits in `test_person_folders.py` abgedeckt). Deckt alle 5 geforderten Szenarien plus
`bulk_assign_person_job` extra.

ruff: grün. mypy: keine neuen Fehler (siehe oben). Tests: 46/46 grün
(neue Datei + alle betroffenen Bestandsdateien), 13 Baseline-rote Tests (comfyui/caption_config,
unabhängig von diesem Plan) unverändert rot — verifiziert per `git stash`.
