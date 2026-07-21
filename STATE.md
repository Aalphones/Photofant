# STATE

**Aktiver Plan:** `docs/planning/2026-07-20_p38-gemma-web-discovery/`
**Phase:** 5/8 — Wissen-Übersicht nach Design (Komplexität: standard → `sonnet` reicht)
**Nächster Schritt:** `phase-5-wissen-uebersicht.md` lesen und umsetzen. Vorher `/clear`
empfohlen (Session ist groß) — danach `/model sonnet`, `/implement` liest hier weiter.

## Phase 4 erledigt (Routen + Guards + neue Aufgaben-Arten) — Live-Smoke steht aus

Code fertig, `ruff`/`mypy`/`npx tsc --noEmit` grün, voller Backend-Testlauf ohne neue
Regressionen (438 grün, 13 rot = exakt die bekannte Vorbelastung unten). Sieben AK-Punkte
sind 🟡 **Live-Smoke (User)** — brauchen einen laufenden Server/Browser, den diese Session
(privates Profil) nicht selbst startet. Checkliste + was genau zu prüfen ist:
`phase-4-api-routen.md` → „AK dieser Phase" (alle 🟡 markiert) und „Report-Back" (bekannte
Grenze: Beschreibung/Beziehungen-Übernahme scheitert auf bereits `user`-owned Entities mit
einer Ownership-Meldung in `errors` — bestehendes P22-Verhalten, keine Neuerung).

`domains/personen.yaml` ist jetzt `private: true` (User-Entscheidung vor Phase-4-Start) —
echte Kontakte sind von der Web-Recherche ausgenommen.

## Phase 3 blockiert (KnowledgeDiscoveryJob — Code fertig, Live-Check aussteht)

`jobs/knowledge_discovery_job.py` + `knowledge/slug.py` stehen, `ruff`/`mypy` grün, 23 neue
gemockte Tests grün. Zwei AK bleiben offen, weil kein Gemma-Modell auf dieser Maschine
registriert ist (`resolve_generator(Capability.KNOWLEDGE_DISCOVERY)` → `None`): der echte
Job-Lauf gegen eine reale öffentliche Person und das Parser-Trefferquote-Protokoll (5-10
Läufe). **Entscheidung (User, vor Phase 4):** Phase 4 trotzdem starten, Live-Check nachholen,
sobald irgendwo ein Modell gebunden ist. Details + Tabelle zum Ausfüllen:
`phase-3-discovery-job.md` → „Report-Back".

## Phase 1+2 erledigt (Fundament Web-Recherche, Merkmale + Vollständigkeit)

Websuche (`ddgs`), Capability `KNOWLEDGE_DISCOVERY`, Schalter `ai.autonomy.discovery`
(Default aus), ADR-031. Merkmale als echte Felder mit eigenem Owner pro Feld, Vollständigkeit
als reine Ableitung, ADR-032. Migration 0040 (Cache-Spiegel `knowledge_entities.attributes`)
lief beim ersten App-Start seither mit. Details: `phase-1-fundament.md` / `phase-2-merkmale.md`.

## Vorbelastung (nicht von P38)

- `tests/test_comfyui_run.py` — 9 Fehler auf unverändertem Stand (`run_comfyui_run_job()`
  fehlt ein Argument).
- `tests/test_comfyui_auto_import.py` (3×, `SimpleNamespace` ohne `toggles`) und
  `test_caption_config.py::test_validate_rejects_unimplemented_instruct_mode`.
  Gesamt 13 rote Tests, alle P38-fremd, geprüft auf unverändertem Stand.
- `uv run ruff check .` über das **ganze** Backend meldet 7 Altbestand-Fehler (alte
  Migrationen 0020/0024, `api/assets.py` B008, `inference/tools.py`,
  `jobs/comfyui_run_job.py`). Geänderte Dateien sind grün.
- `backend/photofant/api/persons.py:203` (Zeilennummer kann verschieben) — vorbestehender
  `mypy`-Fehler in `_person_portrait_face_ids` (`dict()` gegen `Sequence[Row[Any]]`),
  verifiziert auf unverändertem Stand vor P38 Phase 4.

## Offene Smoke-Tests (User)

- **P38 Phase 3+4** (siehe oben)
- **P35** GGUF-Gemma-Runtime → `docs/archive/2026-07/2026-07-20_p35-gemma-gguf-runtime/README.md`
- **P26** Empfehlungs-Engine → `docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`
- **Empfehlungs-Cache-Invalidierung** → `docs/archive/2026-07/2026-07-20_recommendation-cache-invalidation/README.md`
- **Lightbox-Tab-Panel** → `docs/archive/2026-07/2026-07-20_lightbox-tabbed-panel.md`

## Backlog

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan steht.
- `docs/planning/2026-07-21_asset-embeddings-auslagern.md` — Galerie-Performance, letzter
  großer Hebel (Bild-Tabelle 90,8 → 11 MB, alle Voll-Abfragen 3-5× schneller). Bereit zum
  Start, hängt an nichts.
