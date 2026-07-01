# Phase 2 — SQLite-Cache + Repositories

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Kontrakt (DB-Cache-Tabellen) · Phase-1-Ergebnis: `schema.py`, `parser.py`, `vault.py`
- Bestand: `db/models.py`, `db/session.py`, `alembic/versions/` (Migrations-Muster), `docs/models.md`, `docs/conventions/python.md`

## AK
- [ ] Alembic-Migration legt `knowledge_entities`/`_relationships`/`_sources`/`_media_links` an; up/down grün.
- [ ] `EntityRepository.upsert_from_vault(entity)` schreibt Entity inkl. Kind-Zeilen in den Cache.
- [ ] `get(id)` / `find_by_alias(alias)` / `search(query, type?, domain?)` liefern korrekt.
- [ ] Kein Cache-Feld ohne Markdown-Entsprechung (Tabelle aus Vault-Datei rekonstruierbar).
- [ ] Löschen einer Entity entfernt alle Kind-Zeilen (kein Waise).

## Umsetzung
- [ ] `db/models.py` — 4 Tabellen (Entity-PK String, Kind-Tabellen FK + Cascade-Delete) + Migration
- [ ] `knowledge/repository.py` — `EntityRepository` + `RelationshipRepository` (Vault-I/O bleibt in `vault.py`)
- [ ] Suche: SQL `LIKE` über title+aliases (FTS optional, nicht Pflicht)
- [ ] Doc: `docs/models.md` (4 Tabellen)
