# Phase 1 — Schema & Settings

**Tier:** standard  
**Status:** pending

---

## Kontext (was vorher lesen)

- `backend/photofant/db/models.py` — `ReviewItem`-Klasse, Spalte `phash_distance`
- `backend/photofant/settings.py` — `AppSettings` TypedDict, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`
- `backend/alembic/versions/0014_phash_duplikaterkennung.py` — Referenz für Migrations-Stil
- ADR-006 (`docs/decisions/006-phash-duplikaterkennung.md`) — Kontext zur bestehenden DHash-Entscheidung

---

## Abnahme-Kriterien

- [ ] `ReviewItem.phash_distance` ist nullable (`Integer`, default `None` für neue Zeilen)
- [ ] `ReviewItem.clip_distance` existiert als `Float`, nullable
- [ ] Bestehende DB-Rows durch Migration unverändert (kein Backfill, kein Datenverlust)
- [ ] `AppSettings` hat `dupe_phash_enabled: bool`, `dupe_clip_enabled: bool`, `dupe_clip_threshold: float`
- [ ] `SETTINGS_DEFAULTS` setzt sinnvolle Defaults: phash aktiv, CLIP aktiv, Schwelle `0.15`
- [ ] `dupe_threshold` bleibt im Schema, wird aber nicht mehr vom Scan gelesen (Altlast; kein Breaking Change)
- [ ] `_EXPECTED_TYPES` validiert alle drei neuen Felder korrekt
- [ ] `patch_settings` wirft `TypeError` bei falschem Typ (bool statt int etc.)

---

## Checkliste

### Migration

- [ ] Neue Alembic-Migration `0017_clip_distance_duale_duplikaterkennung.py` anlegen
- [ ] `op.alter_column("review_item", "phash_distance", nullable=True)` — macht Feld nullable
- [ ] `op.add_column("review_item", sa.Column("clip_distance", sa.Float(), nullable=True))`
- [ ] Downgrade: `clip_distance` entfernen, `phash_distance` zurück auf `NOT NULL` setzen
  - 🟡 Downgrade würde bestehende CLIP-only Rows zerstören — im Downgrade mit Kommentar warnen

### DB-Modell

- [ ] `ReviewItem.phash_distance`: `Mapped[int | None]` (war `Mapped[int]`)
- [ ] `ReviewItem.clip_distance`: `Mapped[float | None]` hinzufügen

### Settings

- [ ] `AppSettings` TypedDict: drei neue Felder hinzufügen
  ```python
  dupe_phash_enabled: bool
  dupe_clip_enabled: bool
  dupe_clip_threshold: float
  ```
- [ ] `SETTINGS_DEFAULTS`: `"dupe_phash_enabled": True`, `"dupe_clip_enabled": True`, `"dupe_clip_threshold": 0.15`
- [ ] `_EXPECTED_TYPES`: `"dupe_phash_enabled": bool`, `"dupe_clip_enabled": bool`, `"dupe_clip_threshold": (float, int)`
- [ ] In `settings.py` nach bestehenden `dupe_threshold`-Einträgen einfügen (Lesbarkeit)

### ADR

- [ ] `docs/decisions/007-duale-duplikaterkennung-clip.md` anlegen (ADR-007)
  - Kontext: ADR-006 erwähnt CLIP als spätere Option
  - Entscheidung: CLIP als optionale zweite Stufe, OR-Logik, beide Scores im UI
  - Konsequenzen: Schema-Erweiterung, Pairwise-Chunking nötig

### Docs

- [ ] `docs/decisions/006-phash-duplikaterkennung.md` — Fußnote ergänzen: „Ergänzt durch ADR-007"

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
