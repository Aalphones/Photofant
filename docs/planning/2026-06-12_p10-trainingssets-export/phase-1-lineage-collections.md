# P10 · Phase 1 — Lineage & Collections-Ausbau

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (lineage)
- [Konzept](../../Konzept-Photofant.md) §10 (Gruppierung nach Original/Face/Edit), §5 (version/face-Verkettung)
- P6 Phase 4 (Collections-Basis), P8 Phase 4 (Versionsketten)

## Akzeptanzkriterien

- Lineage-Endpoint baut den Ableitungs-Baum (Original → Versionen → Faces → deren Versionen) aus `version.parent_id`/`face.source_version_id`.
- Galerie-Gruppierungsmodus „Lineage": Original als Anker, Ableitungen gruppiert; Detail-Panel „Verwandte Assets" (Prototyp-Sektion) zeigt die Lineage.
- Manuelle Alben rund: Reordering, Cover-Wahl, Beschreibung (Prototyp-Karten).

## Checkliste

- [ ] Lineage-Query + Endpoint
- [ ] Gruppierungsmodus im Grid + Verwandte-Sektion im Detail-Panel (`docs/design/js/relation.jsx` als Referenz)
- [ ] Alben-Feinschliff (Cover, Beschreibung)
- [ ] Doc-Update: routes.md

## Report-Back
