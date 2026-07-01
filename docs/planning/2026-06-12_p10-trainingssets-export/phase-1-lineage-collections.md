# P10 · Phase 1 — Lineage & Collections-Ausbau

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (lineage)
- [Konzept](../../Konzept-Photofant.md) §10 (Gruppierung nach Original/Face/Edit), §5 (version/face-Verkettung)
- P6 Phase 4 (Collections-Basis), P8 Phase 4 (Versionsketten)

## Akzeptanzkriterien

- Lineage-Endpoint baut den Ableitungs-Baum (Original → Versionen → Faces → deren Versionen) aus `version.parent_id`/`face.source_version_id`.
- Galerie-Gruppierungsmodus „Lineage": Original als Anker, Ableitungen gruppiert; Detail-Panel „Verwandte Assets" (Prototyp-Sektion) zeigt die Lineage.
- Manuelle Alben rund: Reordering, Cover-Wahl, Beschreibung (Prototyp-Karten).

## Checkliste

- [x] Lineage-Query + Endpoint
- [x] Gruppierungsmodus im Grid + Verwandte-Sektion im Detail-Panel (`docs/design/js/relation.jsx` als Referenz)
- [x] Alben-Feinschliff (Cover, Beschreibung, Reihenfolge)
- [x] Doc-Update: routes.md

## Report-Back

- **Lineage-Endpoint:** `GET /api/assets/{id}/lineage` baut den Baum aus `version.instance_id`
  (Editor-Edits der Instanz) und `face.asset_id` (extrahierte Gesichter) + deren eigenen
  `version.face_id`-Edits. Bewusst getrennt von der bestehenden `original_id`/`linked_edits`-
  Beziehung (ComfyUI-Edits, manuell verknüpft) — beide Mechanismen bleiben nebeneinander
  bestehen, die Lightbox zeigt jetzt beide Sektionen.
- **Gruppierungsmodus „Original/Edit":** nutzt den bereits vorhandenen `stack_group_id`
  (ADR-012) statt eines eigenen Tree-Fetches pro Gruppe — konsistent mit dem bestehenden
  Stapel-Modell, kein N+1-Request-Risiko. Der Gruppierungs-Umschalter im Sub-Toolbar
  (`GROUPS`/`setGroup`) existierte im Code bereits, war aber nirgends im Template verdrahtet —
  als Cycle-Button ergänzt (betrifft auch die 3 bestehenden Modi Monat/Person/Quelle, die
  vorher ebenfalls unerreichbar waren).
- **Alben-Feinschliff:** Migration 0024 (`collection.description`, `collection.cover_asset_id`,
  `collection_item.position`). Reihenfolge bewusst ohne Drag-and-Drop (kein `@angular/cdk` im
  Projekt) — Auf/Ab-Buttons in einer neuen Cover-&-Reihenfolge-Sektion der Album-Einstellungen,
  reiht per `PUT /api/collections/{id}/order` komplett neu ein.
- **Deviation:** Konzept §5 nennt nur `version.parent_id`/`face.source_version_id` als
  Lineage-Quelle; die Instanz-Versionen selbst hängen aber an `version.instance_id`
  (bestehendes Schema, nicht Teil dieser Phase) — der Endpoint nutzt beide Felder wie im
  bereits produktiven `_load_asset_versions`-Muster.
