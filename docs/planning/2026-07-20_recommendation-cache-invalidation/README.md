# Empfehlungs-Cache: gezielte Invalidierung bei Graph-Änderungen

## Problem

`GET /recommendations?asset_id=` (`backend/photofant/api/recommendations.py`) berechnet
nur, wenn der Cache (`recommendation_cache`, Modell `Recommendation` in `db/models.py`) für
das Quell-Asset leer ist. Einmal befüllt, bleibt er stehen — nichts invalidiert ihn, obwohl
`score_pair()` (`recommendation/scoring.py`) von Person-/Rollen-/Film-Zugehörigkeit **beider**
Seiten eines Paares abhängt. Ändert sich diese Zugehörigkeit (neue Personen-Zuordnung, Rolle
verknüpft, Beziehung im Wissensgraph geändert), bleiben die gecachten Empfehlungen für jedes
betroffene Asset falsch — auf unbestimmte Zeit, ohne dass irgendwo ein Job dafür sichtbar wird.
`ADR-026` hat das bewusst auf „später" verschoben (`recommendation_job.py:12-13`); das ist der
„später"-Moment.

## Kontrakt

**Neue Utilities** (Single Source für alle Aufrufer unten):

- `backend/photofant/recommendation/context.py`
  - `assets_of_persons(session: Session, person_ids: list[int]) -> set[int]` — öffentliche
    Umbenennung von `_assets_of_persons` (bisher modul-privat, nur von `gather_graph_candidates`
    genutzt). Verhalten unverändert.
  - **Neu:** `assets_for_entity(session: Session, entity_id: str) -> set[int]` — alle Assets,
    die von einer Entity-Änderung betroffen sind: direkt verknüpfte Assets
    (`KnowledgeMediaLink.kind == "asset"`) **plus** aktive Assets aller Personen, die mit der
    Entity verknüpft sind (`KnowledgeMediaLink.kind == "person"` → `assets_of_persons`).
- `backend/photofant/jobs/recommendation_job.py`
  - **Neu:** `invalidate_recommendations(session: Session, asset_ids: Iterable[int]) -> None` —
    löscht alle `Recommendation`-Zeilen, die eines der Assets **als Quelle oder als
    empfohlenes Ziel** referenzieren (`score_pair` nutzt den Kontext beider Seiten, also ist
    eine Zeile schon stale, wenn nur die Kandidaten-Seite sich ändert). Kein Commit — der
    Aufrufer besitzt die Transaktion, exakt wie `store_recommendations`.

**Aufrufregel für alle Call-Sites (Phasen 2-4):** `invalidate_recommendations(session, ids)`
wird **vor** dem `session.commit()` der jeweiligen Mutation aufgerufen (gleiche Transaktion).
Bei Endpunkten ohne expliziten `session.commit()` (auto-commit über die `get_session`-Dependency,
z. B. `api/knowledge.py`) reicht der Aufruf irgendwo vor dem `return`.

**Architektur-Grenze (bewusst, nicht verhandelbar):** `knowledge/service.py` bleibt frei von
Person-/Asset-Imports (Kommentar in `service.py` bei der `Lore`-Dataclass: „damit dieses Modul
frei von Person-/Asset-/Face-Importen bleibt"). Die Invalidierung für Wissensgraph-Änderungen
lebt deshalb **immer im Aufrufer** (`api/knowledge.py`, `api/persons.py`, `api/assets.py`,
`jobs/knowledge_patch_job.py`) — nie in `KnowledgeService` selbst.

## Overview

| Phase | Thema | Rating | Status |
|---|---|---|---|
| 1 | Core-Utility (`assets_of_persons`, `assets_for_entity`, `invalidate_recommendations`) + ADR | standard | complete |
| 2 | Manuelle Face-/Person-Aktionen (faces, assets, persons, review-queue, bulk-assign) | standard | complete |
| 3 | Wissensgraph-Verknüpfungen (link-entity, relationships, knowledge-patch) | standard | complete |
| 4 | Clustering (automatische Zuordnung nach Import — vermutlicher Hauptverursacher) | standard | pending |

## Finale Akzeptanzkriterien

1. Jede der in Phase 2-4 gelisteten Mutationen löscht vor ihrem Commit die passenden
   `recommendation_cache`-Zeilen (Quelle **und** Ziel-Spalte).
2. `GET /recommendations?asset_id=X` liefert nach einer solchen Mutation für ein betroffenes
   Asset `status=computing` (leerer Cache), nicht mehr die alten Zeilen.
3. Kein bestehender Test bricht; jede Phase bringt mindestens einen neuen Test, der die
   Invalidierung an der jeweiligen Stelle **beweist** (Cache vorher befüllen, Mutation
   auslösen, Cache-Zeilen sind weg).
4. `knowledge/service.py` bleibt unverändert (0 neue Imports von Person/Asset/Face dort).
5. `docs/code-map.md` (Zeile „Empfehlungen") und ein neues ADR dokumentieren den
   Invalidierungs-Mechanismus.

## Smoke-Checkliste (User, am Plan-Ende)

Reihenfolge nach Konfidenz — zuerst prüfen, wo ich am unsichersten war:

1. **🟡 Wackelstelle Clustering (Phase 4):** Ein Foto importieren, das automatisch einer
   bestehenden Person zugeordnet wird (Auto-Match, kein manueller Klick) → vorher für ein
   Nachbar-Asset dieser Person eine Empfehlung abrufen (Cache befüllen), dann importieren,
   dann die Empfehlung erneut abrufen → sollte neu rechnen (`status=computing`, kurz danach
   neue Werte), nicht die alten Zeilen zeigen.
2. Person zwei Bildern manuell neu zuweisen (`PATCH /faces/{id}/assign`) → Empfehlungen für
   das betroffene Bild vorher/nachher vergleichen.
3. Einer Person eine neue Wissens-Entity verknüpfen (Wizard „Verknüpfen") → Empfehlungen für
   eines ihrer Bilder ändern sich (neues `same_role`/`same_film`-Signal möglich).
4. Job-Dock während Schritt 1-3 offen lassen — kurze `recommendation`-Jobs sollten jetzt
   sichtbar aufblitzen (nicht mehr nur beim allerersten Öffnen eines Bildes).

## Konfidenz-Ausweis

- **Clustering (Phase 4):** einzige Stelle, an der ich nicht aus einem bereits bestehenden
  `enqueue_reevaluate_assets`-Muster kopiere, sondern neu sammle (welche Faces haben in
  diesem Lauf den `person_id` gewechselt). Check: der neue Test in Phase 4 (Pre-Match- und
  HDBSCAN-Zweig je einmal) muss beide Zweige treffen, nicht nur einen.
- **`update_entity`-Generic-Patch (Phase 3):** patcht `media_links` theoretisch als Rohfeld
  (selten benutzt, aber `PATCHABLE_FIELDS` erlaubt es). Der Vorher/Nachher-Union-Ansatz
  deckt das ab — Check: Phase-3-Test patcht `media_links` direkt (nicht nur `relationships`)
  und prüft, dass sowohl das alte als auch das neue verknüpfte Asset invalidiert wird.
- Sonst keine wackligen Stellen — der Rest kopiert 1:1 das bestehende
  `enqueue_reevaluate_assets`-Muster an denselben Zeilen.

## Follow-ups (gefunden, bewusst nicht Teil dieses Plans)

- `review_queue.py::resolve_face_review`, Zweig `action == "reject"` (Zeile ~176-190) löst
  bis heute **kein** `enqueue_reevaluate_assets` für Smart-Alben aus, obwohl er `person_id`
  über `reassign_face` ändert — bestehende Lücke, nicht Recommendation-spezifisch. Phase 2
  fixt hier nur die Recommendation-Invalidierung, nicht die Smart-Alben-Lücke.
- `clustering/engine.py`/`clustering_job.py` haben (vor diesem Plan) ebenfalls **keinen**
  `enqueue_reevaluate_assets`-Aufruf für Smart-Alben — Phase 4 fixt nur Recommendations,
  nicht diese Nachbar-Lücke.

## Summary

_(beim Archivieren ausfüllen)_

## Files touched

_(beim Archivieren ausfüllen)_

## Commits

_(beim Archivieren ausfüllen)_

## Deviations from plan

_(beim Archivieren ausfüllen)_
