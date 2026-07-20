# Phase 1 — Core-Utility + ADR

## Kontext (lesen vor dem Start)

- `backend/photofant/recommendation/context.py` — `AssetGraphContext`, `build_context(s)`,
  `gather_graph_candidates`, und ganz unten `_assets_of_persons` (Zeile 206-215, modul-privat).
- `backend/photofant/jobs/recommendation_job.py` — `store_recommendations` (Zeile 34-50) als
  Vorbild: löscht Cache-Zeilen ohne Commit, Aufrufer committet. `Recommendation`-Import bereits
  vorhanden (Zeile 25).
- `backend/photofant/db/models.py` — `Recommendation`-Modell (~Zeile 421-444): Felder
  `source_asset_id`, `recommended_asset_id`.
- `backend/photofant/db/models.py` — `KnowledgeMediaLink` (~Zeile 325-336): Felder `entity_id`,
  `kind` (`"person"`|`"asset"`), `target_id`.
- `backend/tests/test_recommendation_job.py` — bestehendes Testmuster (`db_session`-Fixture,
  `_add_asset`-Helper).
- `docs/decisions/026-recommendation-reason-chain.md` — die ADR, deren „später"-Punkt dieser
  Plan einlöst (kurz gegenlesen, damit das neue ADR sauber referenziert statt dupliziert).

## AK dieser Phase

1. `assets_of_persons` ist öffentlich (kein Unterstrich-Präfix) in `context.py`, Verhalten
   identisch zur bisherigen `_assets_of_persons`. `gather_graph_candidates` nutzt den neuen
   Namen; keine andere Stelle im Code ruft `_assets_of_persons` mehr auf (Grep bestätigt leer).
2. `assets_for_entity(session, entity_id) -> set[int]` existiert in `context.py`, gebaut aus
   zwei Bulk-Queries (kein N+1):
   ```python
   def assets_for_entity(session: Session, entity_id: str) -> set[int]:
       """Assets, die eine Änderung an dieser Entity (Relationship oder Media-Link) betrifft:
       direkt verknüpfte Assets plus aktive Assets aller mit ihr verknüpften Personen."""
       rows = session.execute(
           select(KnowledgeMediaLink.kind, KnowledgeMediaLink.target_id).where(
               KnowledgeMediaLink.entity_id == entity_id
           )
       ).all()
       direct_assets = {target_id for kind, target_id in rows if kind == "asset"}
       person_ids = [target_id for kind, target_id in rows if kind == "person"]
       return direct_assets | assets_of_persons(session, person_ids)
   ```
3. `invalidate_recommendations(session, asset_ids)` existiert in `recommendation_job.py`,
   direkt unter `store_recommendations`:
   ```python
   from collections.abc import Iterable
   from sqlalchemy import or_

   def invalidate_recommendations(session: Session, asset_ids: Iterable[int]) -> None:
       """Löscht recommendation_cache-Zeilen, die eines der Assets als Quelle oder als
       empfohlenes Ziel referenzieren — score_pair() hängt vom Kontext beider Seiten ab,
       also ist eine Zeile schon stale, wenn nur die Kandidaten-Seite sich ändert. Kein
       Commit, siehe store_recommendations."""
       ids = list(asset_ids)
       if not ids:
           return
       session.query(Recommendation).filter(
           or_(
               Recommendation.source_asset_id.in_(ids),
               Recommendation.recommended_asset_id.in_(ids),
           )
       ).delete(synchronize_session=False)
   ```
   (`synchronize_session=False`: kurzlebige Request-Session, kein im Speicher gehaltenes
   `Recommendation`-Objekt aus einer anderen Quelle in dieser Transaktion — `False` ist hier
   sicher und am schnellsten, siehe SQLAlchemy-Doku zu `Query.delete()`.)
4. Neues ADR `docs/decisions/030-recommendation-cache-invalidierung.md` (Format: Kontext /
   Optionen / Entscheidung / Konsequenzen, ~10 Zeilen) — hält fest: gezielte Invalidierung bei
   Graph-Änderungen statt TTL oder manueller Rebuild-Button (die zwei verworfenen Alternativen
   aus dem Nutzer-Entscheid), Begründung: trifft die Ursache statt nur das Symptom, kein neuer
   Wartungs-Screen-Eintrag nötig. Referenziert ADR-026 als den Punkt, der hiermit eingelöst wird.
5. `docs/code-map.md`, Zeile „Empfehlungen": im Backend-Teil bei `recommendation_job.py` einen
   kurzen Halbsatz ergänzen, dass der Cache jetzt bei Graph-Änderungen gezielt invalidiert wird
   (Verweis auf ADR-030), statt nur bei Cache-Miss zu rechnen. Grobheits-Regel beachten: kein
   Aufzählen aller Call-Sites, nur der Mechanismus in einem Halbsatz.

## Tests

In `backend/tests/test_recommendation_job.py` (gleiche Datei, gleiches Fixture-Muster):

- `test_invalidate_recommendations_deletes_rows_where_asset_is_source` — Cache-Zeile mit
  `source_asset_id=100` anlegen, `invalidate_recommendations(session, [100])` aufrufen,
  committen, Zeile ist weg.
- `test_invalidate_recommendations_deletes_rows_where_asset_is_target` — Cache-Zeile mit
  `source_asset_id=100, recommended_asset_id=101` anlegen, `invalidate_recommendations(session,
  [101])` aufrufen (nur das Ziel, nicht die Quelle!) — Zeile muss trotzdem weg sein. Das ist
  der Kern-Fix (bisher wurde nur `source_asset_id` je gelöscht), also der wichtigste Test hier.
- `test_invalidate_recommendations_empty_list_is_noop` — leere Liste, keine Exception, keine
  Zeile gelöscht.

In einer neuen Datei `backend/tests/test_recommendation_context_invalidation.py` (oder als
Ergänzung zu `test_recommendation_scoring.py`, falls dort schon ein passendes Fixture-Setup für
`KnowledgeMediaLink` existiert — vorher kurz nachsehen):

- `test_assets_for_entity_returns_direct_and_person_linked_assets` — eine Entity mit einem
  direkten Asset-Link (`kind="asset"`) und einem Personen-Link (`kind="person"`, die Person hat
  eine aktive `AssetInstance`) anlegen; `assets_for_entity` liefert beide Asset-IDs.
- `test_assets_for_entity_empty_when_unlinked` — Entity ohne jeden `KnowledgeMediaLink` →
  leeres Set.

## Doc-Updates

- [x] `docs/decisions/030-recommendation-cache-invalidierung.md` neu
- [x] `docs/code-map.md` — Zeile „Empfehlungen" ergänzt

## Report-Back

**Status:** ✅ complete (2026-07-20)

- `assets_of_persons` öffentlich (Rename, Verhalten unverändert), `assets_for_entity` neu
  in `context.py` — zwei Bulk-Queries, kein N+1.
- `invalidate_recommendations` neu in `recommendation_job.py`, löscht Quelle **und** Ziel
  (Kern-Fix ggü. dem alten Löschmuster, das nur `source_asset_id` traf).
- **Deviation vom Plantext:** zusätzlich Index `ix_recommendation_target` auf
  `recommendation_cache.recommended_asset_id` (Model + Migration 0039) — die neue Filterung
  auf dieser Spalte war sonst ein Full-Table-Scan; Projekt-Konvention
  (`docs/conventions/python.md`, „Filter-Spalten kriegen ihren Index im selben Change")
  verlangt das explizit. Nicht im Plan-AK stehend, aber direkte Konsequenz der neuen Query.
- ADR-030 hält TTL/Rebuild-Button als verworfene Alternativen fest, referenziert ADR-026.
- Tests: 6 neu (3× `invalidate_recommendations`, 2× `assets_for_entity`, siehe oben) — alle
  grün. `ruff` grün. `mypy --strict`: 7 vorbestehende Fehler in `models.py`/`context.py`
  (unrelated `type: ignore`/`Row`-Typing, verifiziert per `git stash` gegen `master` —
  keine Regression, nicht Teil dieser Phase).
- Volle Backend-Suite: 372 grün, 13 rot — alle 13 vorbestehend auf `master` (comfyui-Run-Worker
  + ein caption-config-Test), verifiziert per `git stash`. Baseline-Gate erfüllt (nichts neu
  kaputt), Fixes außerhalb Scope.
