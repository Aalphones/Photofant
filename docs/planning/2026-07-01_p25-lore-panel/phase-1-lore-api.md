# Phase 1 — Lore-Aggregations-API (Backend)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Kontrakt (`get_lore` voll, REST, Payload) · **P22** (Stub, Repos) · **P24** (media_links)
- Bestand: `api/knowledge.py`, `api/assets.py`, `api/persons.py`, `db/`-Repos

## AK
- [ ] `get_lore(id)` liefert Entity + Relationships mit **aufgelösten** Zielen (Titel + Typ) + verwandte Medien (media_links) + Quellen + Franchises.
- [ ] `GET .../lore?asset_id=` / `?person_id=` liefern die Payload; ohne Verknüpfung → 200 mit `entity: null` (kein 404).
- [ ] „Verwandte Entities" = 1 Hop über Relationships, keine abgeleiteten Beziehungen doppelt (Dok 020 §6).
- [ ] Read-only, keine KI, kein Netzwerk.

## Umsetzung
- [ ] `get_lore` vom Stub zur Vollform (Relationship-Auflösung, Medien-Join)
- [ ] Lore-Route in `api/knowledge.py` + Pydantic-Response-Schema
- [ ] Doc: `docs/routes.md`, `docs/code-map.md`
