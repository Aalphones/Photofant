# Phase 3 — Backend-API: CRUD, Retro-Lauf, Filter/Facets/Suche

**Tier:** standard (Kontrakt klar, Lösungsweg bekannt)

## Kontext (vor Start lesen)

- [`backend/photofant/api/assets.py`](../../../backend/photofant/api/assets.py) — `list_assets` (Filter-Parameter, `_compute_facets`, q-Suche mit `q_mode`), `AssetDetailDto`, `get_asset`. **Das `framing`-Muster (Filter `IN`, Facet-Count) ist die Vorlage.**
- [`backend/photofant/api/tags.py`](../../../backend/photofant/api/tags.py) — Vorlage für CRUD-Router-Stil.
- [`backend/photofant/api/classify.py`](../../../backend/photofant/api/classify.py) — der Rerun-Endpoint, über den der Retro-Lauf läuft (kein neuer Endpoint nötig).
- [`docs/routes.md`](../../../docs/routes.md) — wird in Phase 6 nachgezogen.
- Router-Registrierung: [`backend/photofant/main.py`](../../../backend/photofant/main.py) (oder wo Router includet werden).

## Akzeptanzkriterien

1. `api/classification.py` (prefix `/classification`) liefert die CRUD-Endpoints
   exakt nach Kontrakt (README): Kategorien + Labels anlegen/ändern/löschen,
   GET liefert Kategorien mit verschachtelten Labels (nach `position` sortiert).
   Löschen einer Kategorie/eines Labels räumt abhängige `asset_classification`-Zeilen
   per `ON DELETE CASCADE` mit ab.
2. Router ist in der App registriert; OpenAPI zeigt die Endpoints.
3. `GET /assets` akzeptiert `classification: list[int]` (Label-IDs):
   **OR innerhalb einer Kategorie, AND über Kategorien** (Label-IDs nach
   `category_id` gruppieren, je Gruppe ein `Asset.id IN (...)`-Subquery).
4. `Facets` um `classifications: list[CategoryFacet]` erweitert — je aktiver
   Kategorie die Label-Counts über das aktuelle Ergebnis (analog `tags_top`/`framings`).
5. Freie q-Suche matcht zusätzlich `classification_label.name` — Treffer werden
   zur bestehenden Tag-/Caption-Suche **vereinigt** (nicht ersetzt), damit Labels
   „wie Tags/Captions" suchbar sind.
6. `AssetDetailDto` enthält `classifications` nach Kontrakt (flach, Lightbox
   gruppiert clientseitig nach Kategorie), sortiert nach `confidence` absteigend.
7. Retro-Lauf läuft über `POST /classify/rerun {asset_ids:"all", steps:["categories"]}`
   und liefert eine Job-ID (Phase-2-Job).
8. `ruff` grün; ein API-Test deckt CRUD + den Gruppen-Filter (OR/AND) ab.

## Checkliste

- [ ] `api/classification.py`: Pydantic-DTOs + CRUD-Endpoints; Router in `main.py` registrieren.
- [ ] `api/assets.py`: `classification`-Query-Param + Gruppen-Filter-Logik.
- [ ] `api/assets.py`: `_compute_facets` um Kategorie-Label-Counts erweitern; `Facets`/`CategoryFacet`-Modelle.
- [ ] `api/assets.py`: q-Suche um Label-Namen-Union erweitern.
- [ ] `api/assets.py`: `AssetDetailDto.classifications` + Laden in `get_asset` (eine Query mit Joins über `asset_classification` → label → category).
- [ ] Tests: `backend/tests/test_classification_api.py` (CRUD + Filter-Gruppierung).

## Report-Back
