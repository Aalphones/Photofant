# P6 · Phase 4 — Smart-Alben & Alben-View

> Rating: **heikel** (Neubewertungs-Trigger sitzen an vielen Stellen; vergessene Hooks = stille Inkonsistenz) · Status: complete

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

- [x] Migrationen + Collection-CRUD + Trigger-CRUD (Migration 0012, `api/collections.py`)
- [x] Bewertungs-Engine (Asset gegen Trigger-Sets; Batch-Variante für Trigger-Änderung) — `collections/engine.py`
- [x] Hooks an allen Mutationspfaden (Tag-Edit, Caption-Edit, Bulk, Merge, Tagging-/Caption-Job für Import+Rerun, Trigger-CRUD)
- [x] Alben-View + Trigger-Editor-Dialog + `collections`-Slice
- [x] Bulk-Bar-Aktion „Zu Album hinzufügen"
- [x] Doc-Update: routes.md, docs/models.md

> **Tests:** Im private-Profil werden keine Integrationstests geschrieben (dokumentierte
> Projekt-Ausnahme). Die Engine wurde stattdessen mit einem Wegwerf-Skript funktional
> verifiziert (any/all, Auto-Raus bei Tag-Entfernung, manuelles Mitglied überlebt, Negate).

## Report-Back

- **Schema:** Migration 0012 (`collection`, `smart_trigger`, `collection_item`) nach Konzept §5.
- **Engine** (`collections/engine.py`): `compute_smart_members` (Set-Algebra, Batch) +
  `evaluate_collection` / `evaluate_asset`. Trigger-Semantik 1:1 aus dem Prototyp.
- **Job** (`jobs/collections_job.py`, JobKind `reevaluate`): per-Asset- und per-Collection-Neubewertung über die Queue.
- **Hooks:** API-seitig an Tag-/Caption-Edit, Bulk-Tag, Tag-Merge; im Tagging-/Caption-Job
  (deckt Initial-Import **und** Rerun-Ergebnisse ab); an Trigger-CRUD + Modus/Smart-Toggle.
- **Person-Trigger:** Schema + UI vorhanden, bis P7 inaktiv (matchen nichts, UI-Tab ausgegraut).
- **Frontend:** `collections`-Slice (Entity-Adapter + Detail), Alben-View (Overview/Detail/Gear-Panel
  mit Trigger-Editor), Galerie-`collection_id`-Filter (Rail-Facette + Chip + URL-stabil),
  Bulk-Bar „Zu Album".
