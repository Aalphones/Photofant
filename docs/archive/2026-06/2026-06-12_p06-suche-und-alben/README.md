# P6 — Suche & Alben (Stage 2c)

> Status: complete · Quelle: [Konzept](../../Konzept-Photofant.md) §10 · Abhängigkeiten: P5

Die in P5 erzeugten Daten werden bedienbar: vollständige Filter-Rail, 3-Modi-Suche, Tag-Verwaltung mit manueller Korrektur, Smart-Alben mit automatischem Rein & Raus. Überwiegend Frontend-Arbeit auf fertigen Backend-Daten.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Filter-Facetten](phase-1-filter-facetten.md) | standard | complete |
| 2 | [3-Modi-Suche](phase-2-suche.md) | standard | complete |
| 3 | [Tag-Verwaltung & Korrektur](phase-3-tag-verwaltung.md) | standard | complete |
| 4 | [Smart-Alben](phase-4-smart-alben.md) | heikel | complete |

## Kontrakt (Backend ↔ Frontend)

- **`GET /api/assets`-Erweiterung (additiv):** Filter-Params `tags` (ids, AND), `source`, `quality_min`, `q` + `q_mode` (`tags|caption|semantic`), `collection_id`; Response zusätzlich `facets: { sources: [{value, count}], tags_top: [...] }` für die Rail-Counts.
- **`GET /api/tags?query=&page=`** — Liste mit Nutzungs-Count (Autocomplete + Verwaltung). **`PATCH /api/tags/{id}`** (rename), **`POST /api/tags/merge`** (`{ from_ids, into_id }` → alias_of), **`POST /api/tags/bulk`** (`{ asset_ids, add: [], remove: [] }`).
- **`PATCH /api/assets/{id}/tags`** — `{ add: string[], remove: number[] }` (add by name → upsert `kind = manual`). **`PATCH /api/assets/{id}/caption`** — `{ caption }`. Beide triggern Smart-Album-Neubewertung.
- **`GET/POST/PATCH/DELETE /api/collections`** — `kind: album | smart_album`, `match_mode`; **`GET/POST/DELETE /api/collections/{id}/triggers`** (person/tag/caption, negate), **`POST /api/collections/{id}/reevaluate`**.
- **Neubewertungs-Regel (Backend-intern):** Tag-/Caption-/Personen-Änderung an Asset X → Queue-Job bewertet X gegen alle Smart-Alben; Trigger-Änderung an Album Y → Job bewertet Y gegen alle Assets. Mitgliedschaft materialisiert in `collection_item.source = 'smart'`.

## Finale Akzeptanzkriterien

1. Filter-Rail nach Prototyp: Quelle, Qualität (Slider), Tags (Suchfeld + Checkboxen), Sammlung; aktive Filter als Chips in der Sub-Toolbar, kombinierbar, URL-stabil (Reload behält Filter).
2. Suche in drei Modi mit Mode-Toggle + Autocomplete; semantisch liefert CLIP-Ranking mit Score-Sortierung.
3. Tags pro Bild editierbar (hinzufügen/entfernen); manuelle Tags überleben ein Caption-/Tag-Rerun (Konzept: manuell bevorzugt).
4. Tag-Verwaltung: umbenennen, mergen (Alias bleibt auflösbar), Bulk auf Auswahl.
5. Smart-Album „Tag X ODER Caption enthält Y" füllt sich automatisch; Tag an einem Bild entfernen → Bild fällt beim nächsten Neubewertungs-Lauf raus. Kein manueller Exclude (Konzept §10.1).
6. Alben-View nach Prototyp (Karten, Smart-Badge, Trigger-Editor im Gear-Dialog).

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Filter „Quelle = flux" + Tag + Qualität > 0.5 kombinieren → Ergebnis plausibel, Chips sichtbar, Reload behält alles
- [ ] Semantische Suche „woman in red dress" → vordere Treffer passen
- [ ] Falschen Auto-Tag an einem Bild entfernen → Bild verschwindet aus dem betroffenen Smart-Album
- [ ] Zwei Tags mergen → Suche nach dem Alias findet weiterhin
- [ ] Smart-Album mit zwei Triggern (all-Modus) anlegen → Inhalt entspricht UND-Logik

## Summary

P6 macht die P5-Daten bedienbar: Filter-Rail, 3-Modi-Suche, Tag-Verwaltung mit manueller
Korrektur und Smart-Alben mit automatischem Rein & Raus. Alle vier Phasen umgesetzt; Phase 4
(Smart-Alben) ist der heikle Teil — Neubewertungs-Hooks an jedem Mutationspfad, sonst stille
Inkonsistenz.

## Files touched

**Backend (Phase 4):** `alembic/versions/0012_collections.py`, `db/models.py`,
`collections/engine.py` (neu), `jobs/collections_job.py` (neu), `jobs/queue.py`,
`api/collections.py` (neu), `api/assets.py`, `api/tags.py`, `jobs/tagging_job.py`,
`jobs/caption_job.py`, `main.py`.

**Frontend (Phase 4):** `models/collection.model.ts` (neu), `services/collection.service.ts` (neu),
`store/collections/*` (neu), `features/alben/*` (Alben-View + `album-settings`),
`features/galerie/{galerie,filter-rail,sub-toolbar}`, `ui/bulk-bar/*`, `store/filters/*`,
`store/gallery/*`, `models/job.model.ts`, `app.config.ts`.

## Commits

Siehe `git log` (P6 Phase 1–4, je ein feat-Commit + planning-chore).

## Deviations from plan

- **Keine Integrationstests** (Phase-4-Checkliste nannte welche): private-Profil = keine Tests
  (dokumentierte Projekt-Ausnahme). Engine stattdessen per Wegwerf-Skript funktional verifiziert.
- **Trigger-PATCH** (`PATCH /collections/{id}/triggers/{tid}`) ergänzt, um „negate" sauber zu
  togglen statt Trigger zu löschen + neu anzulegen.
- **Import-Abdeckung:** Neubewertungs-Hook sitzt im Tagging-/Caption-Job — so landen auch
  frisch importierte Bilder automatisch in passenden Smart-Alben (über die Phase-Checkliste hinaus).

## Follow-ups

- Person-Trigger werden mit P7 (Gesichtserkennung) scharf geschaltet — Schema/UI stehen bereits.
- Initial-Bundle-Budget 3 kB über Soll (nur Build-Warnung) — bei Gelegenheit Lazy-Boundaries prüfen.
