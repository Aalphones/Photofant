# Phase 1 — Entities, Beziehungen, Suche + Owner-Semantik

**Komplexität:** heikel (Owner-Semantik + ADR) · **Unterbau:** P22 · **Status:** pending

## Kontext (vor dem Bauen lesen)

- `README.md` dieses Plans — Kernidee, Owner-Entscheidung, Kontrakt, Gate.
- `2026-07-06_mcp-schnittstelle/` (Basisplan) — `mcp/server.py` (Tool-Registrierung), `mcp/adapter.py`
  (`run_endpoint`), `mcp/gate.py` (`confirmation_required`), Settings-Sektion.
- `2026-07-01_p22-knowledge-engine/README.md` — **Kontrakt-Sektion**: `KnowledgeService`-Methoden,
  REST-Endpoints (`/api/knowledge/entities`, `/search`, `/relationships`), Ownership-Regeln,
  Entity-Frontmatter.
- Beim Umsetzen zusätzlich der **reale** `backend/photofant/api/knowledge.py` + `knowledge/service.py`
  (existiert erst nach P22) — Signaturen gegen die Kontrakt-Sektion abgleichen.
- `backend/photofant/settings.py` — MCP-Block (aus Basisplan) um `knowledge_owner` erweitern.

## AK (falsifizierbar)

- [ ] `mcp.knowledge_owner` (enum `manual|web|inferred`, default `manual`) in `settings.py`
      (`AppSettings`, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`) + Frontend-Typ + Dropdown mit i-Tooltip in
      der bestehenden MCP-Settings-Sektion.
- [ ] `backend/photofant/mcp/tools/knowledge.py` registriert an `mcp_server`, alle über `run_endpoint`:
  - [ ] `search_knowledge(query, type?, domain?)` → `GET /api/knowledge/search`; Ergebnis gedeckelt,
        gibt id/title/type/domain/confidence/owner zurück.
  - [ ] `get_entity(ref)` → `GET /api/knowledge/entities/{id}` (ref = id **oder** Alias, Service löst auf).
  - [ ] `create_entity(type, title, aliases?, domain?, body?, relationships?)` → `POST /entities`,
        `owner` = `mcp.knowledge_owner`.
  - [ ] `update_entity(id, patch)` → `PATCH /entities/{id}`, `owner` = `mcp.knowledge_owner`; Ownership
        lehnt Überschreiben höherwertiger Felder ab (Fehler verständlich an den Agenten melden).
  - [ ] `delete_entity(id, confirm=false)` → `DELETE /entities/{id}`. **Gate.**
  - [ ] `add_relationship(id, type, target_ref)` / `remove_relationship(id, type, target_ref, confirm=false)`
        → `POST/DELETE /entities/{id}/relationships`. Remove = **Gate.**
  - [ ] `list_domains()` → verfügbare Domänen/Typen (aus der Domänen-Config, damit der Agent gültige
        `type`/`domain`-Werte kennt statt zu raten).
- [ ] Jedes Tool hat eine präzise Description; die Owner-Folge steht in der Description von `create`/`update`.
- [ ] ADR-020 `docs/decisions/020-mcp-wissensbasis-ownership.md` angelegt.

## Umsetzung — Checkliste

- [ ] Settings-Key `knowledge_owner` (Backend + Frontend + Dropdown).
- [ ] `mcp/tools/knowledge.py` mit den Tools oben; Gate-Tools über `gate.py`.
- [ ] Ownership-Ablehnung sauber in eine Agent-lesbare Fehlermeldung mappen.
- [ ] ADR-020 schreiben.
- [ ] Doc: `docs/code-map.md` (Zeile `mcp/tools/knowledge.py`), `docs/routes.md` (MCP-Wissens-Abschnitt),
      Warnhinweis in der MCP-Settings-Sektion um „…und dein Wissen" ergänzen.

## Report-Back
