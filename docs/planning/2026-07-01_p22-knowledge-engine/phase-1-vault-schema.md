# Phase 1 — Vault + Entity-Schema + Parser

**Komplexität:** heikel (definiert das Kern-Schema für alle späteren Pläne) · **Status:** pending

## Kontext
- README → Kontrakt (Vault-Layout, Entity-Frontmatter) — verbindlich
- Konzept: `../../Konzept-Agentic-Knowledge-Base/020 - Entity Specification.md`, `010 - Knowledge Engine.md` §4
- `docs/conventions/python.md`, `backend/photofant/settings.py`; sauberes Modul-Layout als Vorbild: `media/meta.py`

## AK
- [ ] Entity-Markdown mit dem Frontmatter aus dem Kontrakt wird fehlerfrei geparst (alle Felder typisiert, Listen korrekt).
- [ ] Round-Trip `Entity → Markdown → Entity` verlustfrei (Body inklusive).
- [ ] Validator lehnt ab: fehlende `id`/`type`/`title`, `confidence` außerhalb 0–1, unbekannter `owner`, `type` nicht in der Domäne.
- [ ] Vault-Struktur (`knowledge/`, `domains/`, `prompts/`) wird beim ersten Zugriff angelegt, Pfad aus `settings.knowledge.vaultPath`.
- [ ] `domains/movies.yaml` definiert Entity-/Relationship-Types; Engine-Code enthält keinen davon hart.

## Umsetzung
- [ ] Paket `backend/photofant/knowledge/`: `schema.py`, `parser.py`, `validator.py`, `domains.py`, `vault.py`
- [ ] `domains/movies.yaml` als Beispiel-Domäne
- [ ] settings-Keys `knowledge.vaultPath`, `knowledge.defaultDomain` (Defaults, freigegeben)
- [ ] Frontmatter über etablierte Lib (`python-frontmatter`/`pyyaml`) — Dependency via `mode-dependencies` klären
- [ ] Doc: `docs/code-map.md` (Zeile Wissensbasis), ADR-010 `docs/decisions/010-knowledge-vault.md`
