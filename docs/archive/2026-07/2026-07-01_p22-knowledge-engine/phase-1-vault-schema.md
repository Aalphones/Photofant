# Phase 1 — Vault + Entity-Schema + Parser

**Komplexität:** heikel (definiert das Kern-Schema für alle späteren Pläne) · **Status:** complete

## Kontext
- README → Kontrakt (Vault-Layout, Entity-Frontmatter) — verbindlich
- Konzept: `../../Konzept-Agentic-Knowledge-Base/020 - Entity Specification.md`, `010 - Knowledge Engine.md` §4
- `docs/conventions/python.md`, `backend/photofant/settings.py`; sauberes Modul-Layout als Vorbild: `media/meta.py`

## AK
- [x] Entity-Markdown mit dem Frontmatter aus dem Kontrakt wird fehlerfrei geparst (alle Felder typisiert, Listen korrekt).
- [x] Round-Trip `Entity → Markdown → Entity` verlustfrei (Body inklusive — auch mit `---`-Trennlinie im Body verifiziert).
- [x] Validator lehnt ab: fehlende `id`/`type`/`title`, `confidence` außerhalb 0–1, unbekannter `owner`, `type` nicht in der Domäne.
- [x] Vault-Struktur (`knowledge/`, `domains/`, `prompts/`) wird beim ersten Zugriff angelegt, Pfad aus `settings.knowledge.vault_path` (`open_vault()`/`get_vault_path()`).
- [x] `domains/movies.yaml` definiert Entity-/Relationship-Types; Engine-Code enthält keinen davon hart.

## Umsetzung
- [x] Paket `backend/photofant/knowledge/`: `schema.py`, `parser.py`, `validator.py`, `domains.py`, `vault.py`
- [x] `domains/movies.yaml` als Beispiel-Domäne
- [x] settings-Keys `knowledge.vault_path`, `knowledge.default_domain` (Defaults; **snake_case** statt der im Plan notierten camelCase — siehe FINDINGS)
- [x] Frontmatter über `python-frontmatter` (+ `pyyaml` für Domänen, `types-PyYAML` dev) — isoliert hinter `parser.py`
- [x] Doc: `docs/code-map.md` (Zeile Wissensbasis), **ADR-025** `docs/decisions/025-knowledge-vault-markdown-wahrheit.md` (nicht 010 — belegt, siehe FINDINGS)

## Ergebnis / Verifikation
Alle AK per Wegwerf-Skript geprüft (Round-Trip inkl. `---`-Body, alle Validator-Ablehnungen), `mypy --strict` + `ruff` grün. Kein Live-Test (private-Profil) — Smoke-Checkliste am Plan-Ende (nach Phase 4) durch den User.
