# P22 — Knowledge Engine

> Roadmap-Phase 1 aus dem Konzept `docs/Konzept-Agentic-Knowledge-Base/` (Dok 010, 020). **Backend-Fundament, keine KI.** Erster von sechs Backlog-Plänen (P22–P27) für die agentische Wissensbasis. **Hält den geteilten Kontrakt** für P23–P27. *(private-Profil, lean.)*

## Ziel

Generische Wissensbasis: Markdown = einzige Wahrheit, SQLite = jederzeit neu aufbaubarer Cache, eine Service-API, über die alle späteren Jobs/UIs Wissen lesen/schreiben. Die Engine kennt keine KI, keine Modelle, keine Typen wie „Film" — nur Entity + Type + Relationship, Typ kommt aus einer Domäne.

## Scope

**Drin:** Markdown-Vault (`knowledge/`) mit Entity-Format + Parser/Serializer + Validator · SQLite-Cache-Tabellen + Alembic-Migration · `KnowledgeService` + REST `api/knowledge.py` (CRUD Entity/Relationship, Titel/Alias-Suche) · Ownership-/Confidence-Regeln · Rebuild-Job + Vault↔Cache-Reconcile in die Wartung · Domänen als Config, ausgeliefert mit Beispiel „Movies".

**Draußen (Follow-ups):** 🟡 **Markdown-Embeddings / semantische Wissenssuche** — bewusst verschoben, MVP+Recommendation braucht sie nicht (Empfehlungen laufen über die vorhandene Bild-CLIP-Suche + Graph). Spart die Embedding-Modell-Baustelle. · KI/Gemma → **P27** · jede UI → ab P23.

## Kontrakt (Single Source für P23–P27)

Downstream liest **diese Sektion**, nicht den Code. Änderungen hier = Vertragsbruch, in P23–P27 nachziehen.

**Vault-Layout & Entity-Datei**
```
knowledge/
  <type-plural>/<entity-slug>.md   # eine Datei = eine Entity
  domains/<domain>.yaml            # Entity-Types + Relationship-Types
  prompts/                         # leer (später P27)
```
Entity-Frontmatter (verbindlich, Dok 020 §5): `id` (`<type>/<slug>`, unveränderlich), `type`, `title`, `aliases[]`, `status`, `owner` (user|manual|web|inferred), `confidence` (0.0–1.0), `domain`, `media_links{persons[],assets[]}`, `relationships[{type,target}]`, `sources[]`. Body = freier Markdown darunter.

**DB-Cache (Namespace `knowledge_*`, reiner Cache):** `knowledge_entities`, `knowledge_relationships`, `knowledge_sources`, `knowledge_media_links`. Alles aus dem Vault neu aufbaubar. (P23 ergänzt `knowledge_tasks`, P26 `recommendation_cache`.)

**Service `knowledge/service.py` → `KnowledgeService`:** `create_entity(payload, owner)` · `update_entity(id, patch, owner)` · `delete_entity(id)` · `find_entity(ref)` (id **oder** alias) · `search_entities(query, type?, domain?)` · `create_relationship`/`remove_relationship` · `link_media`/`unlink_media` (P24) · `get_lore(id)` (**Stub hier, Ausbau P25**).
- **Ownership:** Priorität `user > manual > web > inferred`. Schreibzugriff mit niedrigerer Owner-Priorität überschreibt nicht (MVP: Ablehnung). User = immer `confidence 1.0`.
- **Mutations-Regel:** jede Persistenz über den Service, Markdown-first, nie direkt DB/Datei.

**REST:** `GET/POST /api/knowledge/entities` · `GET/PATCH/DELETE .../{id}` · `GET .../search?q=&type=&domain=` · `POST/DELETE .../{id}/relationships` · `POST/DELETE .../{id}/media-links` · `GET .../{id}/lore`.

**Frontend (P23 legt real an, hier reserviert):** `models/knowledge.model.ts` · `store/knowledge/` · `services/knowledge.service.ts` · `features/wissen/` · `jobs/knowledge_*_job.py` (Namens-Parallelität nach `code-map.md`).

## Reservierte Entscheidungen & Settings

**ADR (real in `docs/decisions/` anlegen):**
- **ADR-025** — Vault: Markdown = Wahrheit, SQLite = Cache. *(Phase 1 angelegt. Die im Plan ursprünglich reservierte Nummer 010 war bereits belegt — echte nächste freie Nummer ist 025, siehe FINDINGS.)*
- **Intelligente Jobs erweitern die Job-Queue statt Agenten-Framework** — real ab P24, bekommt dort die dann freie ADR-Nummer (die ursprünglich reservierte 011 ist ebenfalls belegt).

**settings.json (vorab freigeben, snake_case wie der Rest von `settings.py`):** `knowledge.vault_path` (Default `<data_root>/knowledge`) · `knowledge.default_domain` (Default `Movies`) · `jobs.max_depth` (Job-Ketten-Tiefe, Dok 030 §11, Default 5; erst von P24 angelegt). *(Ursprünglich als `vaultPath`/`defaultDomain` notiert — auf snake_case korrigiert, siehe FINDINGS.)*

## Phasen

| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Vault + Entity-Schema + Parser | heikel | ✅ complete |
| 2 | SQLite-Cache + Repositories | standard | ✅ complete |
| 3 | KnowledgeService + REST-API | standard | ✅ complete |
| 4 | Rebuild-Job + Vault↔Cache-Reconcile | standard | pending |

Strikt sequenziell (jede Phase konsumiert die vorige).

## Finale AK (Gesamt)
- [ ] Entity als Markdown anlegen, per REST lesen/suchen/ändern/löschen — Änderung immer Markdown-first, dann Cache.
- [ ] Cache komplett löschbar und aus dem Vault identisch neu aufbaubar.
- [ ] Schreibzugriff mit niedrigerer Owner-Priorität überschreibt keinen höheren Wert.
- [ ] Beispiel-Domäne „Movies" definiert Typen; Engine-Code enthält keine Domänen-Typen hart.

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. `curl POST /api/knowledge/entities` mit Beispiel-Entity → Datei liegt unter `knowledge/actors/…md`.
2. `curl GET .../search?q=RDJ` findet sie über den Alias.
3. Cache-Tabellen leeren → Rebuild in der Wartung auslösen → Suche findet die Entity wieder.
4. `PATCH` mit `owner=inferred` auf ein user-Feld → wird abgelehnt.

## Risiken
- 🟡 **Vault↔Cache-Drift** bei Hand-Edits → Reconcile-Job (Phase 4), Markdown gewinnt.
- 🟡 **ID-Stabilität:** `id` fix, `slug`/`title` änderbar → Umbenennung = Move + Cache-Update, nie ID-Wechsel.
- 🟡 **Offene Konzept-Entscheidungen** (Dok 020 §15: Relationship-Metadaten) → MVP simpel (Relationship = nur type+target), FINDINGS falls P26 mehr braucht.

## Chesterton
Berührt additiv: `jobs/queue.py` (neue Job-Typen), `db/models.py`+Alembic, `maintenance/`, `settings.py`. Kein Bestandscode ersetzt/entfernt — kein Fence-Risiko.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_
- Follow-up: Markdown-Embeddings / semantische Wissenssuche · Relationship-Metadaten falls P26 es braucht.
