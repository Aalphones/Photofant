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

- [x] `api/classification.py`: Pydantic-DTOs + CRUD-Endpoints; Router in `main.py` registrieren.
- [x] `api/assets.py`: `classification`-Query-Param + Gruppen-Filter-Logik.
- [x] `api/assets.py`: `_compute_facets` um Kategorie-Label-Counts erweitern; `Facets`/`CategoryFacet`-Modelle.
- [x] `api/assets.py`: q-Suche um Label-Namen-Union erweitert (im `q_mode=text`-Zweig, gleichrangig zu Tag-/Personen-/Caption-Treffern).
- [x] `api/assets.py`: `AssetDetailDto.classifications` + Laden in `get_asset` (eine Query mit Joins über `asset_classification` → label → category, sortiert nach `confidence` absteigend).
- [x] Tests: `backend/tests/test_classification_api.py` (CRUD + explizites Cascade-Delete + OR/AND-Filter + Facet/Detail/Suche).

## Report-Back

- CRUD: `api/classification.py` — Kategorien/Labels anlegen, ändern, löschen. Da `PRAGMA foreign_keys=ON` projektweit aus ist (FINDINGS.md), löschen `delete_category`/`delete_label` die abhängigen `asset_classification`-/`classification_label`-Zeilen **explizit** im Python-Code, nicht über das deklarierte `ON DELETE CASCADE`. Regressionstest dafür vorhanden.
- Filter: `GET /assets?classification=<label_id>&...` gruppiert die Label-IDs nach Kategorie (`ClassificationLabel.category_id`) und verkettet je Gruppe einen `Asset.id IN (...)`-Subquery-Filter — OR innerhalb, AND über Kategorien, wie im Kontrakt.
- Facets: neue `_compute_classification_facets` liefert je aktiver (enabled) Kategorie die Label-Counts über das aktuelle gefilterte Ergebnis — gleiches Muster wie `tags_top`/`framings`.
- q-Suche: nur der `q_mode=text`-Zweig (die globale Freitextsuche) wurde um einen Label-Namen-Treffer erweitert — `q_mode=tags` bleibt unverändert (reine Tag-Suche laut Kontrakt-Kommentar im Code).
- Retro-Lauf: kein neuer Code nötig — `steps: ["categories"]` war schon in Phase 2 verdrahtet (`ClassifyStep`, `rerun_job.py`).
- Abweichung vom Plan: keine.
- Tests: `uv run pytest` — 189 passed, 13 vorbestehende Fehlschläge in `test_caption_config.py`/`test_comfyui_*` (bestätigt bereits auf `master` rot, nicht Teil dieser Phase). `uv run ruff check .` — nur vorbestehende Fehler in Alembic-Migrationen/`comfyui_run_job.py`/dem alten `File(...)`-B008 in `assets.py`, nichts Neues.
