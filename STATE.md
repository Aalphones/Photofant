# STATE

**Aktiver Plan:** `docs/planning/2026-07-20_p38-gemma-web-discovery/`
**Phase:** 3/8 — KnowledgeDiscoveryJob (Suche → Gemma → Fakten-Vorschläge) — pending
**Nächster Schritt:** `phase-3-*.md` lesen und umsetzen; der Wackelpunkt ist der Parser-Test
(5-10 echte Läufe, Trefferquote protokollieren, bevor Phase 4 draufbaut). Phase 3 ist **heikel**
→ `/model opusplan` empfohlen.

## Phase 2 erledigt (Merkmale + Vollständigkeit)

Merkmale sind jetzt echte Felder mit **eigenem Owner pro Feld**: neuer `attributes`-Block im
Frontmatter (Round-Trip mit Umlauten/Doppelpunkt/langen Werten verlustfrei geprüft), Felder pro
Entity-Typ in der Domänen-YAML (`fields:`), Vollständigkeit als reine Ableitung (nie gespeichert),
eigener Schreibweg `set_attributes()` der ein `user`-Merkmal gegen einen `web`-Lauf schützt und
die Entity-Ownership unangetastet lässt. ADR-032 angelegt. **Abweichung vom Plan:** Merkmale
liegen zusätzlich als JSON-Spiegel in `knowledge_entities.attributes` (**migration 0040**) —
sonst hätte die unpaginierte Personen-Liste für jeden Prozentwert eine Markdown-Datei geöffnet.
Neue Tests `backend/tests/test_knowledge_attributes.py` (10, grün). Details: `phase-2-merkmale.md`
(Report-Back).

⚠️ **Migration 0040 ist noch nicht auf der laufenden DB** — beim nächsten App-Start/`alembic
upgrade head` läuft sie mit.

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
- Dazu **4 weitere rote Tests**, ebenfalls auf dem unveränderten Stand geprüft (2026-07-21):
  `test_comfyui_auto_import.py` (3× — `SimpleNamespace` ohne `toggles` in `api/comfyui.py:641`)
  und `test_caption_config.py::test_validate_rejects_unimplemented_instruct_mode`. Gesamt-Suite
  steht damit bei 13 roten Tests, alle P38-fremd.
- `uv run ruff check .` über das **ganze** Backend meldet 7 Altbestand-Fehler (alte Migrationen
  0020/0024, `api/assets.py` B008, `inference/tools.py`, `jobs/comfyui_run_job.py`). Die
  geänderten Dateien sind grün; die CI-Zeile aus `AGENTS.md` läuft aber rot durch.

## Offene Smoke-Tests (User)

- **P35** GGUF-Gemma-Runtime → `docs/archive/2026-07/2026-07-20_p35-gemma-gguf-runtime/README.md`
- **P26** Empfehlungs-Engine → `docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`
- **Empfehlungs-Cache-Invalidierung** → `docs/archive/2026-07/2026-07-20_recommendation-cache-invalidation/README.md`
- **Lightbox-Tab-Panel** → `docs/archive/2026-07/2026-07-20_lightbox-tabbed-panel.md`

## Backlog

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan steht.
