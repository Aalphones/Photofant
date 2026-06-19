# Phase 3 — On-Demand-Scan-Job + Review-API

## Kontext (vor Implementierung lesen)

- `docs/planning/2026-06-19_duplikaterkennung/README.md` — Kontrakt: alle API-Endpunkte
- `backend/photofant/jobs/queue.py` — `JobKind`, `job_queue.enqueue`, `JobStatus`-Muster
- `backend/photofant/jobs/import_job.py` — Muster für Job-Implementierung
- `backend/photofant/media/phash.py` — `hamming_distance`, `find_similar` (Phase 1+2)
- `backend/photofant/db/models.py` — `ReviewItem`, `Asset` (Phase 1)
- `backend/photofant/api/` — Muster für FastAPI-Router
- `backend/photofant/media/moves.py` + bestehende Delete-Logik — für `delete_a`/`delete_b` Auflösung

## Akzeptanzkriterien

1. `POST /api/jobs/dupe-scan` nimmt `{ scope: 'all' | 'selection', asset_ids?: number[] }` entgegen und stellt einen `DUPE_SCAN`-Job in die Queue.
2. Der Job iteriert alle relevanten Asset-Paare (scope=all: alle Assets; scope=selection: nur übergebene IDs), vergleicht pHashes, legt `review_item`-Einträge an (Unique-Constraint schützt vor Doppeln).
3. `GET /api/review/dupes` gibt alle unresolved `review_item` mit Typ `dupe_candidate` zurück, inklusive vollständiger Asset-Daten beider Seiten (Thumbnail-URL, Dimensionen, Datum, Source).
4. `PATCH /api/review/dupes/{id}` mit `{ resolution }` führt die gewählte Aktion aus:
   - `a_is_original`: setzt `asset_b.original_id = asset_a.id`
   - `b_is_original`: setzt `asset_a.original_id = asset_b.id`
   - `delete_a`: ruft bestehende Soft-Delete-Logik für Asset A auf
   - `delete_b`: ruft bestehende Soft-Delete-Logik für Asset B auf
   - `dismiss`: keine Asset-Änderung
   - Immer: setzt `review_item.resolved_at = now()`, `review_item.resolution = …`
5. `GET /api/assets/{id}/similar` gibt Assets mit pHash-Distanz ≤ Threshold zurück (für Lightbox-Einzelsuche, ad-hoc ohne review_item).
6. Alle Endpunkte liefern HTTP 404 wenn review_item oder Asset nicht existiert.

## Checkliste

### Backend — Scan-Job

- [x] `backend/photofant/jobs/queue.py` — `DUPE_SCAN` zu `JobKind` hinzufügen
- [x] `backend/photofant/jobs/dupe_scan_job.py` anlegen:
  - `run_dupe_scan_job(status, scope, asset_ids)` — Coroutine
  - scope=all: alle Assets mit pHash aus DB laden; scope=selection: gefiltert auf `asset_ids`
  - Alle-gegen-alle Hamming-Vergleich in Python (nested loop, normiertes Paar a<b), chunked mit asyncio.to_thread
  - Unique-Constraint-konforme Einträge anlegen (on_conflict_do_nothing)
  - Progress-Updates via `job_queue.update()`
  - `enqueue_dupe_scan(scope, asset_ids)` Hilfsfunktion
- [x] `backend/photofant/api/jobs.py` — `POST /api/jobs/dupe-scan` ergänzt

### Backend — Review-API

- [x] `backend/photofant/api/review.py` anlegen (neuer Router):
  - `GET /api/review/dupes` — JOIN auf ReviewItem + asset_a; asset_b via session.get
  - `PATCH /api/review/dupes/{id}` — Resolution-Handler mit allen 5 Aktionen (inkl. moves.soft_delete)
  - `GET /api/assets/{id}/similar` — ad-hoc pHash-Suche via find_similar
- [x] Router in `backend/photofant/main.py` eingebunden
- [x] Bestehende Delete-Logik (`moves.soft_delete`) wiederverwendet

### Docs

- [x] `docs/routes.md` — neue Endpunkte eingetragen

## 🟡 Risiko: N²-Performance

Scope=all mit N=10.000 Assets → ~50M Vergleiche, ca. 10-20 Sekunden. Läuft als Hintergrund-Job → kein Problem. Fortschritt per `job_queue.update()` sichtbar machen, damit der User nicht denkt, der Job hängt.

## Report-Back

Phase 3 complete (2026-06-19). Alle 3 Backend-Checkboxen und Docs erledigt. Ruff lint grün.

Implementierungs-Detail: Die Vergleichsschleife läuft in `asyncio.to_thread`-Chunks à 200 äußere
Iterationen — gibt Event-Loop-Breaks für Progress-Updates ohne Overhead für kleine Bestände.
