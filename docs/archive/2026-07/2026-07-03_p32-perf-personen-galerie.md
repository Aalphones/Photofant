# P32 — Performance: Personen-Seite, Personen-Suche, Galerie-Ballast

**Ziel:** Die Personen-Unterseite und alles Personen-/Tag-bezogene Filtern wird schnell.
Vier Ursachen, alle Backend: zwei fehlende Indexe, ein N+1 in der Personen-Liste,
Embedding-BLOBs, die jede Galerie-Seite unnötig mitschleppt.

**Kontext (Befund, verifiziert 2026-07-03):**

1. `asset_instance.person_id` hat keinen Index — der Unique-Constraint `(asset_id, person_id)`
   greift nicht (person_id ist kein Präfix). Trifft: `GET /persons` (Counts), Galerie-Filter
   `person_id` (`api/assets.py`, Filter in `list_assets`), Freitextsuche über Personennamen
   (`q_mode=text`, ebenfalls `list_assets`).
2. `asset_tag.tag_id` hat keinen Index — nur `asset_id`. Trifft: Tag-Filter der Galerie und
   Tag-Namen-Suche (`_tag_name_match_subquery`, beide Such-Modi TAGS + TEXT). `asset_tag`
   ist die größte Tabelle (Assets × Dutzende Tags).
3. `GET /persons` (`api/persons.py`, `list_persons` → `_build_person_dto`) feuert **3 Queries
   pro Person** (count, fav_count, Portrait-Face). 300 Personen ≈ 900 Queries, die Counts
   davon je ein Full Scan wegen (1).
4. `Asset.clip_embedding` (~3 KB float32-BLOB) und `Face.embedding` werden bei jedem
   Entity-Load mitgelesen. Die Galerie-Merge-Strategie holt `page × page_size` Zeilen aus
   zwei Streams (`list_assets`, Merge-Zweig) — tiefes Scrollen zieht tausende Zeilen à 3 KB
   pro Request. Die Faces-Galerie lädt 500 Faces/Seite, jede mit Embedding-Blob.

**Chesterton-Check (was ersetzt wird, verstanden):**

- `_build_person_dto`-Einzelqueries: Zweck ist schlicht Counts + bestes Portrait pro Person —
  keine versteckte Logik, 1:1 durch gruppierte Aggregate ersetzbar. DTO-Form bleibt identisch.
- Die Merge-Pagination (`fetch_limit = page * page_size`) bleibt **unangetastet** — sie ist
  dokumentiert korrekt (Top-N beider Streams bestimmen die Seite). Wir nehmen ihr nur den
  Blob-Ballast; Keyset-Pagination ist bewusst NICHT Teil dieses Plans (erst messen, ob nach
  dem Blob-Fix noch nötig → Follow-up).

**Deferred-Sicherheit (Konsumenten-Sweep, erledigt — Sonnet muss NICHT neu auditieren):**
Alle Leser der beiden Blob-Spalten sind entweder explizite Spalten-Selects (umgehen
`deferred`): `clustering/engine.py:95,254`, `jobs/dupe_scan_job.py:140`, `api/duplicates.py:78`,
beide `rebuild_index` (raw SQL) — oder Einzel-Objekt-Zugriffe (ein Lazy-Load pro Request,
unkritisch): `api/faces.py:311-314`, `api/review.py:231`, `api/search.py:65-73`,
`clustering/engine.py:49-52`, `jobs/embedding_job.py:41` (Schreibzugriff).

---

## Overview

| Phase | Inhalt | Tier | Status |
|---|---|---|---|
| 1 | Indexe + deferred BLOB-Spalten (Migration + models.py) | mechanisch | complete |
| 2 | `GET /persons` ohne N+1 (Aggregat-Umbau) | standard | complete |

---

## Phase 1 — Indexe + deferred Spalten (mechanisch)

**Zu lesen vorab:** `backend/photofant/db/models.py` ·
`backend/alembic/versions/0028_gallery_search_performance.py` (Vorlage Index-Migration) ·
`docs/conventions/python.md`

**Checkliste:**

- [x] `db/models.py`: `AssetInstance.person_id` → `index=True`.
- [x] `db/models.py`: `AssetTag.__table_args__` → `Index("ix_asset_tag_tag_id", "tag_id")` ergänzen.
- [x] `db/models.py`: `Asset.clip_embedding` und `Face.embedding` → `deferred=True`
      (`mapped_column(LargeBinary, nullable=True, deferred=True)`).
- [x] Neue Alembic-Migration `perf_person_tag_indexes` (`0030`): **Abweichung vom Plan** —
      legt nur `ix_asset_instance_person_id` an. `ix_asset_tag_tag_id` existierte bereits seit
      Migration 0028 (Raw-SQL, nur im ORM-Modell nachgezogen) — beim Umsetzen entdeckt, per
      `alembic current` verifiziert (DB stand noch bei 0027, 0028+0029 waren committet aber nie
      angewendet). Erneutes Anlegen hätte beim Upgrade gecrasht.
- [x] `uv run alembic upgrade head` + einmal `downgrade -1` / `upgrade head` (up/down grün).
- [x] `cd backend && uv run ruff check .` grün (nur Pre-Existing-Findings in unbeteiligten
      Dateien); bestehende Backend-Tests laufen lassen (147 passed, 12 pre-existing failures
      in ComfyUI/Caption-Tests — verifiziert unverändert gegen den Stand vor dieser Phase).
- [x] Doc-Update: `docs/models.md` — Index-Spalten bei `asset_instance` und `asset_tag` nachgezogen,
      deferred-Hinweis bei den beiden Embedding-Spalten ergänzt.

**AK Phase 1:**

- `EXPLAIN QUERY PLAN` für `SELECT COUNT(*) FROM asset_instance WHERE person_id = ?`
  zeigt Index-Nutzung (kein `SCAN asset_instance`); dito `asset_tag WHERE tag_id = ?`.
- Eine Galerie-Seite (`GET /api/assets?page=1`) liest die Blob-Spalten nicht mehr mit
  (nachweisbar via SQLAlchemy-Echo: kein `clip_embedding` in der SELECT-Spaltenliste).
- Semantische Suche, Duplikat-Scan, Clustering und Face-Matches funktionieren unverändert
  (die gesweepten Konsumenten oben — Stichprobe reicht: eine semantische Suche, ein Face-Match).

## Phase 2 — `GET /persons` ohne N+1 (standard)

**Zu lesen vorab:** `backend/photofant/api/persons.py` (komplett) ·
`docs/routes.md` (Persons-Sektion) · `docs/conventions/python.md`

**Umbau:**

`list_persons` lädt alle Personen mit **einer** Query und baut die DTOs aus **drei**
gruppierten Zusatz-Queries statt 3 × N:

1. Counts: `SELECT person_id, COUNT(*) FROM asset_instance WHERE deleted_at IS NULL GROUP BY person_id`
2. Fav-Counts: dito mit `favourite = 1` (oder beide in einer Query via `SUM(CASE …)`/`func.sum` — Umsetzer-Wahl)
3. Portrait pro Person: bestes Face je `person_id` (höchster `score`, NULLs zuletzt) — via
   Window-Function `row_number() OVER (PARTITION BY person_id ORDER BY score DESC NULLS LAST)`
   und Filter `= 1`. SQLite kann das seit 3.25, kein Kompatibilitätsrisiko.

`_build_person_dto` bleibt für die Einzel-Person-Pfade (`create`, `update`) erhalten —
3 Queries für **eine** Person sind fein. Alternativ auf die Aggregat-Helper umstellen,
wenn es den Code netto vereinfacht; kein Zwang.

**Checkliste:**

- [x] `api/persons.py`: `list_persons` auf Aggregat-Queries umbauen (DTO-Form unverändert:
      gleiche Felder, gleiche Sortierung `is_unknown ASC, id ASC`). Umgesetzt als 2 gruppierte
      Queries (`_person_instance_counts` mit `func.sum(case(...))` für count+fav_count in einer
      Query, `_person_portrait_face_ids` mit `row_number() OVER (PARTITION BY person_id ...)`)
      statt der im Plan skizzierten 3 — spart eine Query gegenüber dem Vorschlag.
- [x] Personen ohne Instanzen/Faces liefern weiterhin `count=0`, `fav_count=0`,
      `portrait_face_id=None` (LEFT-Semantik: Maps mit `.get(person_id, 0)`, nicht INNER JOIN).
      Per Ad-hoc-Smoke verifiziert (In-Memory-SQLite, 3 Personen inkl. eine ohne Fotos, eine
      mit Soft-Deleted-Instanz): Zahlen und Query-Count (3 total: Persons + Counts + Portraits)
      stimmen.
- [x] `cd backend && uv run ruff check .` grün (persons.py sauber; 6 pre-existing Findings in
      assets.py/comfyui_run_job.py unberührt); Backend-Tests: 147 passed, 12 pre-existing
      Failures (ComfyUI/Caption, identisch zu Phase 1) — keine Regression.
- [x] Doc-Check: `docs/routes.md` (Personen-Sektion, Zeile 594-613) — Response-Shape (`PersonDto`)
      unverändert, verifiziert. Hinweis: die dortige Sortierungs-Notiz („benannt nach Count desc")
      war schon vor dieser Phase falsch (Ist-Code sortiert `is_unknown ASC, id ASC`, wie Plan es
      auch für diese Phase vorschreibt) — laut Plan „nur verifizieren, nichts umschreiben",
      daher unangetastet gelassen; Drift ist pre-existing, nicht durch P32 entstanden.

**AK Phase 2:**

- `GET /persons` setzt eine konstante Zahl Queries ab (4), unabhängig von der Personen-Anzahl.
- Response ist feldgleich zum Ist-Stand: gleiche `count`/`fav_count`-Werte, gleiches
  `portrait_face_id` (höchster Score, NULL-Scores zuletzt), gleiche Sortierung.
- Personen ohne Fotos erscheinen weiterhin mit `count=0`.

---

## Smoke-Checkliste (User, nach Plan-Ende)

- [ ] Personen-Seite lädt spürbar schnell (vorher: mehrere Sekunden).
- [ ] Stichprobe 2-3 Personen: Foto-Anzahl + Favoriten-Zahl auf der Karte stimmen, Porträts unverändert.
- [ ] Klick auf Person → Galerie filtert schnell.
- [ ] Freitextsuche nach einem Personennamen: Ergebnis schnell + korrekt.
- [ ] Galerie-Filter nach einem Tag: schnell.
- [ ] Galerie tief scrollen (10+ Seiten): bleibt flüssig.
- [ ] Semantische Suche funktioniert. Ein Face-Match-Dialog (Dupe-Check) funktioniert.

## Risiken & bewusst NICHT im Scope

- 🟡 `deferred` heißt: greift doch jemand künftig in einer Schleife auf `.embedding` zu,
  entsteht ein stilles N+1 pro Zugriff statt eines fetten Loads. Konvention ab jetzt:
  Embedding-Zugriffe in Schleifen immer als expliziter Spalten-Select.
- 🟡 Einfacher Index auf `person_id` statt Composite `(person_id, deleted_at)`:
  bewusst — `deleted_at` ist unselektiv, der schmale Index reicht und bleibt wartungsarm.
- **Nicht im Scope** (Follow-ups, nur bei Bedarf): Keyset-Pagination der Galerie ·
  Frontend-Virtualisierung der Personen-Karten · Request-pro-Karte + fehlendes Limit bei
  `GET /persons/{id}/faces` (Karten-Modi „Einzelfoto"/„4er-Grid").

---

## Summary

_(beim Archivieren füllen)_

## Files touched

## Commits

## Deviations from plan

## Follow-ups
