# Phase 3 — KnowledgeService + REST-API

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Kontrakt (Service-Methoden, REST-Routen, Ownership) · Phase 1/2: `vault`, `parser`, `validator`, `repository`
- Bestand: `api/` (Router-Muster z.B. `api/tags.py`), `main.py` (Router-Registrierung), `docs/routes.md`

## AK
- [ ] `KnowledgeService` implementiert alle Kontrakt-Methoden; jede Mutation schreibt **Markdown-first**, dann Cache.
- [ ] Ownership-Check: `update_entity(owner=inferred)` gegen `owner=user`-Wert wird abgelehnt.
- [ ] REST: `POST` legt an (201), `GET .../search?q=` findet über Titel/Alias, `PATCH` ändert, `DELETE` entfernt.
- [ ] `create_relationship` schreibt in die Quell-Entity; `get_lore(id)` liefert als **Stub** Entity + direkte Relationships (Ausbau P25).
- [ ] Alles ohne KI, ohne Netzwerk.

## Umsetzung
- [ ] `knowledge/service.py` (orchestriert vault + repository + validator, Ownership durchsetzen)
- [ ] `api/knowledge.py` + Registrierung in `main.py`; Pydantic-Schemas
- [ ] `get_lore` als Stub mit `# P25 erweitert`-Marker
- [ ] Doc: `docs/routes.md`, `docs/code-map.md`
