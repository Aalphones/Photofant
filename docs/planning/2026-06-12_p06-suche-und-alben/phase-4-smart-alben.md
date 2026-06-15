# P6 · Phase 4 — Smart-Alben & Alben-View

> Rating: **heikel** (Neubewertungs-Trigger sitzen an vielen Stellen; vergessene Hooks = stille Inkonsistenz) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (collections/triggers, Neubewertungs-Regel)
- [Konzept](../../Konzept-Photofant.md) **§10.1 komplett**, §5 (collection, smart_trigger, collection_item)
- `docs/design/js/albums.jsx`

## Akzeptanzkriterien

- Migrationen: `collection`, `smart_trigger`, `collection_item` nach Konzept §5 (training_set-Kind kommt in P10, Schema jetzt).
- Trigger-Typen Tag + Caption funktionsfähig; Person-Trigger im Schema + UI vorhanden, aber bis P7 inaktiv (ausgegraut mit Hinweis).
- Neubewertung als Queue-Job; **jeder** Mutationspfad hängt am Hook: Tag-Edit, Caption-Edit, Bulk-Tagging, Merge/Alias, Rerun-Ergebnisse, Trigger-Änderung. Checkliste der Hook-Stellen im Code kommentarlos vollständig — Prüfung per Test: jede Mutation → Album-Stand korrekt.
- `match_mode` any/all + `negate` pro Trigger; manuelles und smart-Mitglied koexistieren (`source`-Spalte), kein manueller Exclude.
- Alben-View nach Prototyp: Karten, manuelle Alben befüllbar (Bulk-Bar „Zu Album"), Smart-Konfiguration im Gear-Dialog (Trigger-Liste + Modus).
- Galerie filterbar nach Collection (`collection_id`).

## Checkliste

- [ ] Migrationen + Collection-CRUD + Trigger-CRUD
- [ ] Bewertungs-Engine (Asset gegen Trigger-Sets; Batch-Variante für Trigger-Änderung)
- [ ] Hooks an allen Mutationspfaden + Integrationstests (Tag weg → raus aus Album; Caption-Edit → rein)
- [ ] Alben-View + Trigger-Editor-Dialog + `collections`-Slice
- [ ] Bulk-Bar-Aktion „Zu Album hinzufügen"
- [ ] Doc-Update: routes.md, docs/models.md

## Report-Back
