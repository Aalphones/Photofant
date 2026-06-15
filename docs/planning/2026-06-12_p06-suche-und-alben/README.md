# P6 — Suche & Alben (Stage 2c)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §10 · Abhängigkeiten: P5

Die in P5 erzeugten Daten werden bedienbar: vollständige Filter-Rail, 3-Modi-Suche, Tag-Verwaltung mit manueller Korrektur, Smart-Alben mit automatischem Rein & Raus. Überwiegend Frontend-Arbeit auf fertigen Backend-Daten.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Filter-Facetten](phase-1-filter-facetten.md) | standard | pending |
| 2 | [3-Modi-Suche](phase-2-suche.md) | standard | pending |
| 3 | [Tag-Verwaltung & Korrektur](phase-3-tag-verwaltung.md) | standard | pending |
| 4 | [Smart-Alben](phase-4-smart-alben.md) | heikel | pending |

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

## Files touched

## Commits

## Deviations from plan

## Follow-ups
