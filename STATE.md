# STATE

**Aktiver Plan:** `docs/planning/2026-07-20_p38-gemma-web-discovery/`
**Phase:** 2/8 — Merkmale + Vollständigkeit (Schema, Felddefinitionen, ADR-032) — pending
**Nächster Schritt:** `phase-2-merkmale.md` lesen und umsetzen; erster AK-Punkt ist der
Frontmatter-Round-Trip mit Sonderzeichen (Doppelpunkt, Umlaute, langer Text).

## Phase 1 erledigt (Fundament Web-Recherche)

Websuche steht: `inference/web_search.py` (Paket `ddgs` 9.14.4 als neue Extra-Gruppe
`web-discovery`, API real gegen die installierte Version geprüft — Keys stimmen),
neue Fähigkeit `KNOWLEDGE_DISCOVERY` mit eigenem Schalter `ai.autonomy.discovery`
(**Default aus**), Prompt `knowledge_discovery.md` v1, ADR-031 angelegt, P27-Offline-AK
amendiert. ruff grün, keine neuen mypy-Fehler. Details: `phase-1-fundament.md` (Report-Back).

## Vorbelastung (nicht von P38)

- `tests/test_comfyui_run.py` ist **vor** dieser Phase schon rot (9 Fehler auf dem
  unveränderten Stand — `run_comfyui_run_job()` fehlt ein Argument). Unabhängig von P38,
  wartet auf eine eigene Runde.

## Offene Smoke-Tests (User)

- **P35** GGUF-Gemma-Runtime → `docs/archive/2026-07/2026-07-20_p35-gemma-gguf-runtime/README.md`
- **P26** Empfehlungs-Engine → `docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`
- **Empfehlungs-Cache-Invalidierung** → `docs/archive/2026-07/2026-07-20_recommendation-cache-invalidation/README.md`
- **Lightbox-Tab-Panel** → `docs/archive/2026-07/2026-07-20_lightbox-tabbed-panel.md`

## Backlog

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan steht.
