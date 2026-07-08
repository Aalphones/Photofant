# Phase 2 — SQLite-Cache + Repositories

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Kontrakt (DB-Cache-Tabellen) · Phase-1-Ergebnis: `schema.py`, `parser.py`, `vault.py`
- Bestand: `db/models.py`, `db/session.py`, `alembic/versions/` (Migrations-Muster), `docs/models.md`, `docs/conventions/python.md`

## AK
- [x] Alembic-Migration legt `knowledge_entities`/`_relationships`/`_sources`/`_media_links` an; up/down grün.
- [x] `EntityRepository.upsert_from_vault(entity)` schreibt Entity inkl. Kind-Zeilen in den Cache.
- [x] `get(id)` / `find_by_alias(alias)` / `search(query, type?, domain?)` liefern korrekt.
- [x] Kein Cache-Feld ohne Markdown-Entsprechung (Tabelle aus Vault-Datei rekonstruierbar).
- [x] Löschen einer Entity entfernt alle Kind-Zeilen (kein Waise).

## Umsetzung
- [x] `db/models.py` — 4 Tabellen (Entity-PK String, Kind-Tabellen FK, **kein** `ON DELETE CASCADE` — SQLite-FK-Enforcement ist projektweit aus, siehe Finding) + Migration `0034_knowledge_cache.py`
- [x] `knowledge/repository.py` — `EntityRepository` + `RelationshipRepository` (Vault-I/O bleibt in `vault.py`)
- [x] Suche: SQL `LIKE` über title+aliases (JSON-Text-Cast, FTS optional, nicht Pflicht)
- [x] Doc: `docs/models.md` (4 Tabellen), `docs/code-map.md`

## Ergebnis / Verifikation
Alembic `upgrade head`/`downgrade -1`/`upgrade head` gegen eine Wegwerf-SQLite manuell geprüft
(Skript verworfen) — alle 4 Tabellen legen sauber an/ab. `EntityRepository`/`RelationshipRepository`
über 7 pytest-Tests abgesichert (`backend/tests/test_knowledge_repository.py`: Upsert inkl.
Kind-Zeilen-Ersatz ohne Duplikate, `get`, exakter Alias-Match ohne Teilstring-Kollision, Suche mit
Typ-/Domain-Filtern, Lösch-Cascade ohne Waisen, Relationship-Repository vor-/rückwärts) —
Testpflicht laut `docs/conventions/testing.md` überstimmt hier das sonst agentenlos-testfreie
private-Profil (Layering-Override). `mypy --strict`: 0 neue Fehler auf den angefassten Dateien
(Projekt-Baseline hat 124 vorbestehende, unabhängige Fehler). `ruff`: grün.
