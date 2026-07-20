# Phase 3 — Wissensgraph-Verknüpfungen

Voraussetzung: Phase 1 (Utilities) committed. Betrifft alles, was `roles`/`films` im
`AssetGraphContext` ändert: Personen↔Entity-Links, Asset↔Entity-Links, Relationships einer
Entity, und der generische Entity-Patch. **Architektur-Grenze:** `knowledge/service.py` wird
in dieser Phase **nicht** angefasst — jede Invalidierung passiert im Aufrufer (`api/knowledge.py`,
`api/persons.py`, `api/assets.py`, `jobs/knowledge_patch_job.py`).

## Kontext (lesen vor dem Start)

- `backend/photofant/recommendation/context.py` — `assets_of_persons`, `assets_for_entity`
  (Phase 1).
- `backend/photofant/jobs/recommendation_job.py` — `invalidate_recommendations` (Phase 1).
- `backend/photofant/api/persons.py` — `link_person_entity` (Zeile ~313-334),
  `unlink_person_entity` (Zeile ~337-359).
- `backend/photofant/api/assets.py` — `link_asset_entity` (Zeile ~1151-1171),
  `unlink_asset_entity` (Zeile ~1174-1197).
- `backend/photofant/api/knowledge.py` — `create_relationship` (Zeile ~453-469),
  `remove_relationship` (Zeile ~472-488), `update_entity` (Zeile ~537-551),
  `delete_entity` (Zeile ~554-561). Beachte: diese Endpunkte haben **keinen** expliziten
  `session.commit()` — Commit passiert automatisch am Ende der `get_session`-Dependency
  (`backend/photofant/db/session.py::get_session`, Zeile 12-21). Der Invalidierungs-Aufruf
  muss also nur **vor dem `return`** stehen, egal wo genau.
- `backend/photofant/jobs/knowledge_patch_job.py` — `_run_patch` (Zeile ~42-65): eigener
  `session.commit()` bei Zeile ~64.
- `backend/photofant/knowledge/service.py` — `PATCHABLE_FIELDS` (Zeile ~34-36):
  `{"title", "aliases", "status", "confidence", "media_links", "relationships", "sources",
  "body"}`. Nur `relationships`/`media_links` sind für Empfehlungen relevant (die anderen
  ändern keinen Score-Input).

## AK dieser Phase

1. **`persons.py::link_person_entity`** / **`unlink_person_entity`** — nach erfolgreichem
   `service.link_media(...)`/`service.unlink_media(...)`-Aufruf (vor `session.commit()`):
   ```python
   from photofant.recommendation.context import assets_of_persons
   from photofant.jobs.recommendation_job import invalidate_recommendations
   ...
   invalidate_recommendations(session, assets_of_persons(session, [person_id]))
   ```
2. **`assets.py::link_asset_entity`** / **`unlink_asset_entity`** — analog, aber das Asset ist
   direkt bekannt (kein Personen-Fan-out): `invalidate_recommendations(session, [asset_id])`
   vor dem jeweiligen `session.commit()`.
3. **`knowledge.py::create_relationship`** — nach `service.create_relationship(...)`:
   ```python
   from photofant.recommendation.context import assets_for_entity
   from photofant.jobs.recommendation_job import invalidate_recommendations
   ...
   invalidate_recommendations(session, assets_for_entity(session, entity_id))
   ```
   (Kein Vorher/Nachher nötig — eine neue Relationship kann nur neue Treffer erzeugen, keine
   bestehenden entfernen, und die betroffene Asset-Menge selbst — wer mit der Entity verlinkt
   ist — ändert sich durch eine Relationship nicht.)
4. **`knowledge.py::remove_relationship`** — identisch zu 3 (dieselbe Begründung: die
   Relationship beeinflusst nur `films`, nicht die Menge der über `roles` verknüpften Assets).
5. **`knowledge.py::update_entity`** — Vorher/Nachher-Union, weil ein generischer Patch von
   `media_links` auch **Entfernungen** enthalten kann:
   ```python
   patch = body.to_patch()
   needs_invalidation = bool({"relationships", "media_links"} & patch.keys())
   before_ids = assets_for_entity(session, entity_id) if needs_invalidation else set()
   ...
   entity = service.update_entity(entity_id, patch, owner)
   ...
   if needs_invalidation:
       invalidate_recommendations(
           session, before_ids | assets_for_entity(session, entity_id)
       )
   ```
   `before_ids` **vor** dem `service.update_entity(...)`-Aufruf berechnen (sonst ist der alte
   Zustand schon überschrieben).
6. **`knowledge.py::delete_entity`** — Assets **vor** dem Löschen ermitteln (danach sind die
   `KnowledgeMediaLink`-Zeilen weg):
   ```python
   affected = assets_for_entity(session, entity_id)
   service.delete_entity(entity_id)
   invalidate_recommendations(session, affected)
   ```
7. **`knowledge_patch_job.py::_run_patch`** — gleiches Vorher/Nachher-Muster wie Punkt 5, aber
   für das Single-Field-Patch dieses Jobs. Vor `service.update_entity(entity_id, {field:
   value}, owner)` (Zeile ~53):
   ```python
   needs_invalidation = field in ("relationships", "media_links")
   before_ids = assets_for_entity(session, entity_id) if needs_invalidation else set()
   ```
   Nach dem `update_entity`-Aufruf, vor `session.commit()` (Zeile ~64):
   ```python
   if needs_invalidation:
       from photofant.jobs.recommendation_job import invalidate_recommendations
       invalidate_recommendations(
           session, before_ids | assets_for_entity(session, entity_id)
       )
   ```

## Tests

Neue Datei `backend/tests/test_recommendation_invalidation_knowledge.py`:

- `test_link_person_entity_invalidates_all_person_assets` — Person mit zwei aktiven Assets,
  Cache-Zeile für beide vorab anlegen, `link_person_entity` aufrufen → beide Zeilen weg.
- `test_create_relationship_invalidates_linked_assets` — Entity mit einem Personen-Link (Person
  hat ein aktives Asset), Cache-Zeile für dieses Asset vorab anlegen, `create_relationship`
  aufrufen → Zeile weg.
- `test_update_entity_media_links_removal_invalidates_old_and_new` — Entity zunächst mit
  Person A verlinkt (Cache-Zeile für A's Asset vorab anlegen), dann per `update_entity`-Patch
  `media_links` auf Person B umschreiben (A entfernt, B hinzugefügt) → **beide** Assets
  (A und B) sind invalidiert. Das ist der in der README genannte Konfidenz-Check.
- `test_knowledge_patch_job_relationships_invalidates` — `_run_patch` mit `field="relationships"`
  direkt aufrufen (wie `test_recommendation_job.py` Funktionsaufrufe nutzt, kein HTTP nötig).
- `test_create_relationship_type_field_patch_is_noop` — `update_entity` mit einem Patch, der
  nur `title` ändert (nicht `relationships`/`media_links`) → keine Cache-Zeile wird gelöscht
  (negativer Test, damit `needs_invalidation` nicht versehentlich immer `True` ist).

## Doc-Updates

Keine zusätzlichen — Phase 1 deckt `code-map.md`/ADR ab.

## Report-Back

Alle 7 Call-Sites umgesetzt: `persons.py::link_person_entity`/`unlink_person_entity`
(`assets_of_persons`-Fan-out), `assets.py::link_asset_entity`/`unlink_asset_entity`
(direktes Asset), `knowledge.py::create_relationship`/`remove_relationship`
(`assets_for_entity` nach dem Service-Call), `update_entity` (Vorher/Nachher-Union bei
`relationships`/`media_links`-Patch, sonst No-op), `delete_entity` (Assets vor dem
Löschen ermittelt), `knowledge_patch_job.py::_run_patch` (gleiches Vorher/Nachher-Muster
fürs Single-Field-Patch). `knowledge/service.py` unverändert (Architektur-Grenze hält).

Neue Testdatei `test_recommendation_invalidation_knowledge.py` (5 Tests, u.a. der
Konfidenz-Check `media_links`-Removal alt+neu invalidiert, und ein Negativ-Test für
reine Titel-Patches). Alle 5 grün. Voller Testlauf: 383 passed, 13 pre-existing Failures
in `test_caption_config.py`/`test_comfyui_*.py` (unberührt von dieser Phase). ruff auf
den geänderten Dateien sauber (ein Alt-Finding in `assets.py:1491`, weit weg von den
Änderungen). mypy: keine neuen Fehler in den 4 geänderten Dateien (16 Alt-Fehler, alle
außerhalb der geänderten Zeilen).
