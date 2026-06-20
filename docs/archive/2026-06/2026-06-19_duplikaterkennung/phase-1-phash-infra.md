# Phase 1 — pHash-Infra + Migration

## Kontext (vor Implementierung lesen)

- `docs/planning/2026-06-19_duplikaterkennung/README.md` — Kontrakt: DB-Schema, Tabellen
- `backend/photofant/db/models.py` — SQLAlchemy-Modelle (`Asset`, bestehende Spalten)
- `backend/alembic/versions/0013_drop_app_config_to_settings_json.py` — Muster für neue Migration
- `backend/photofant/media/meta.py` — `read_meta`, `ImageMeta` — hier oder in neuem `phash.py` die Berechnung anlanden
- `backend/photofant/settings.py` + `backend/settings.example.json` — neues Setting `dupe_threshold`
- `docs/decisions/` — ADR-006 anlegen (nächste freie Nummer nach 001, 004, 005; 002+003 in Backlog-Plänen reserviert)

## Akzeptanzkriterien

1. Migration `0014_phash_duplikaterkennung.py` läuft durch (`uv run alembic upgrade head`).
2. `asset.phash` (INTEGER nullable) und `asset.original_id` (INTEGER FK → asset.id nullable) existieren in der DB.
3. `review_item`-Tabelle mit allen Spalten und Unique-Constraint `(type, asset_a_id, asset_b_id)` existiert.
4. SQLAlchemy-Modelle `Asset` und `ReviewItem` in `models.py` reflektieren die neuen Spalten/Tabelle.
5. `imagehash` in `pyproject.toml` + `uv.lock` eingetragen.
6. `backend/photofant/media/phash.py` mit `compute_phash(path: Path) -> int` — gibt 64-Bit-Integer zurück.
7. ADR-006 angelegt: pHash (imagehash DHash) als Ähnlichkeits-Metrik, Alternativen (CLIP Cosine, aHash, pHash) mit Trade-offs.
8. `dupe_threshold` in `photofant/settings.py` als Feld mit Default `10` + Validierung (0–20); `settings.example.json` aktualisiert.

## Checkliste

### Backend

- [x] `imagehash` zu `pyproject.toml` hinzufügen; `uv lock` ausführen
- [x] `backend/photofant/media/phash.py` anlegen:
  - `compute_phash(path: Path) -> int` — öffnet Bild mit Pillow, berechnet DHash (8x8), gibt `int` zurück
  - `hamming_distance(a: int, b: int) -> int` — `bin(a ^ b).count('1')`
- [x] `backend/photofant/db/models.py` — `Asset` um `phash` + `original_id` erweitern
- [x] `backend/photofant/db/models.py` — `ReviewItem` anlegen:
  - Felder: id, type, asset_a_id FK, asset_b_id FK, phash_distance, created_at, resolved_at, resolution
  - Unique-Constraint: `(type, asset_a_id, asset_b_id)`
- [x] Migration `0014_phash_duplikaterkennung.py` schreiben (idempotent — SQLite-FK-Trap umgangen)
- [x] `photofant/settings.py` — `dupe_threshold: int` mit Default `10` ergänzen
- [x] `settings.example.json` — `"dupe_threshold": 10` eintragen
- [x] `uv run alembic upgrade head` — läuft durch
- [x] `uv run ruff check .` — sauber

### Docs

- [x] ADR-006 schreiben: `docs/decisions/006-phash-duplikaterkennung.md`
- [x] `docs/models.md` — `asset.phash`, `asset.original_id`, `review_item`-Tabelle eintragen

## Report-Back
