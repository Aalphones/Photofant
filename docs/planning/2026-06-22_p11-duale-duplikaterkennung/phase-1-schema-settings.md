# Phase 1 — Schema & Settings

**Tier:** standard  
**Status:** complete

---

## Kontext (was vorher lesen)

- `backend/photofant/db/models.py` — `ReviewItem`-Klasse, Spalte `phash_distance`
- `backend/photofant/settings.py` — `AppSettings` TypedDict, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`
- `backend/alembic/versions/0014_phash_duplikaterkennung.py` — Referenz für Migrations-Stil
- ADR-006 (`docs/decisions/006-phash-duplikaterkennung.md`) — Kontext zur bestehenden DHash-Entscheidung

---

## Abnahme-Kriterien

- [x] `ReviewItem.phash_distance` ist nullable (`Integer`, default `None` für neue Zeilen)
- [x] `ReviewItem.clip_distance` existiert als `Float`, nullable
- [x] Bestehende DB-Rows durch Migration unverändert (kein Backfill, kein Datenverlust)
- [x] `AppSettings` hat `dupe_phash_enabled: bool`, `dupe_clip_enabled: bool`, `dupe_clip_threshold: float`
- [x] `SETTINGS_DEFAULTS` setzt sinnvolle Defaults: phash aktiv, CLIP aktiv, Schwelle `0.15`
- [x] `dupe_threshold` bleibt im Schema, wird aber nicht mehr vom Scan gelesen (Altlast; kein Breaking Change)
- [x] `_EXPECTED_TYPES` validiert alle drei neuen Felder korrekt
- [x] `patch_settings` wirft `TypeError` bei falschem Typ (bool statt int etc.)

---

## Checkliste

### Migration

- [x] Neue Alembic-Migration `0025_clip_distance_duale_duplikaterkennung.py` anlegen (Nummer 0017 aus dem Plan war überholt — Head stand bei 0024)
- [x] `phash_distance` nullable via `batch_alter_table` (SQLite verlangt Batch-Mode für `ALTER COLUMN`, siehe Referenz-Migration 0007)
- [x] `op.add_column("review_item", sa.Column("clip_distance", sa.Float(), nullable=True))`
- [x] Downgrade: `clip_distance` entfernen, `phash_distance` zurück auf `NOT NULL` setzen
  - 🟡 Downgrade würde bestehende CLIP-only Rows zerstören — im Downgrade mit Kommentar warnen

### DB-Modell

- [x] `ReviewItem.phash_distance`: `Mapped[int | None]` (war `Mapped[int]`)
- [x] `ReviewItem.clip_distance`: `Mapped[float | None]` hinzufügen

### Settings

- [x] `AppSettings` TypedDict: drei neue Felder hinzufügen
  ```python
  dupe_phash_enabled: bool
  dupe_clip_enabled: bool
  dupe_clip_threshold: float
  ```
- [x] `SETTINGS_DEFAULTS`: `"dupe_phash_enabled": True`, `"dupe_clip_enabled": True`, `"dupe_clip_threshold": 0.15`
- [x] `_EXPECTED_TYPES`: `"dupe_phash_enabled": bool`, `"dupe_clip_enabled": bool`, `"dupe_clip_threshold": (float, int)`
- [x] In `settings.py` nach bestehenden `dupe_threshold`-Einträgen einfügen (Lesbarkeit)

### ADR

- [x] `docs/decisions/007-duale-duplikaterkennung-clip.md` anlegen (ADR-007)
  - Kontext: ADR-006 erwähnt CLIP als spätere Option
  - Entscheidung: CLIP als optionale zweite Stufe, OR-Logik, beide Scores im UI
  - Konsequenzen: Schema-Erweiterung, Pairwise-Chunking nötig

### Docs

- [x] `docs/decisions/006-phash-duplikaterkennung.md` — Fußnote ergänzen: „Ergänzt durch ADR-007"

---

## Report-Back

- Migration heißt `0025_...` statt `0017_...` (Plan-Nummer war beim Schreiben aktuell, Head ist seither auf 0024 gewandert).
- Migration + Downgrade gegen Wegwerf-SQLite verifiziert (upgrade head, Spalten-Check via `PRAGMA table_info`, downgrade -1) — nicht gegen echte Nutzdaten.
- `uv run pytest` zeigt 12 rote Tests (`test_comfyui_run.py`, `test_caption_config.py`, `test_comfyui_auto_import.py`) — bestehen bereits auf `master` vor dieser Phase (per `git stash` verifiziert), nicht durch P11 verursacht. Nicht angefasst (out of scope).
