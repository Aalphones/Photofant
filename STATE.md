# STATE

**Aktiver Plan:** `docs/planning/2026-07-20_p38-gemma-web-discovery/`
**Phase:** 3/8 — KnowledgeDiscoveryJob — 🟡 Code+Tests fertig, zwei AK-Punkte blockiert
**Nächster Schritt:** 🔴 Entscheidung nötig, bevor Phase 4 startet — siehe „Phase 3 blockiert"
unten. Kurzfassung: `gemma-3-12b-obliterated-gguf` ist auf dieser Maschine nicht gebunden, der
echte Job-Lauf + Parser-Trefferquote-Test (Konfidenz-Ausweis README Punkt 1) kann daher nicht
laufen. Modell binden und Check nachholen, oder Phase 4 auf eigenes Risiko ohne diesen Check
starten.

## Phase 3 blockiert (KnowledgeDiscoveryJob — Code fertig, Live-Check aussteht)

`jobs/knowledge_discovery_job.py` + `knowledge/slug.py` stehen, `ruff`/`mypy` grün, 23 neue
gemockte Tests grün (`test_knowledge_discovery_job.py`, `test_knowledge_slug.py`). Zwei AK
bleiben offen, weil kein Gemma-Modell auf dieser Maschine registriert ist
(`resolve_generator(Capability.KNOWLEDGE_DISCOVERY)` → `None`): der echte Job-Lauf gegen eine
reale öffentliche Person und das Parser-Trefferquote-Protokoll (5-10 Läufe). Details + Tabelle
zum Ausfüllen: `phase-3-discovery-job.md` → „Report-Back".

**Nebenbefund (User-Entscheidung vor Phase 4):** Die Domäne „Personen" (echte private
Kontakte, z. B. `Person/anna-lieb`) ist nicht `private: true` markiert — anders als die
separate Domäne „Private". Sobald Phase 4 die Route freischaltet, wäre Web-Recherche auf
diesen echten Kontakten technisch erlaubt. Klären, ob das gewollt ist.

**Neu, nicht im ursprünglichen Plan-Codeblock:** `PrivateDomainError` in `knowledge/service.py`
(Phase 4 muss sie zu 422 fangen); `DiscoveryOutput` trägt zusätzlich ein `errors`-Feld
(Parser-Hinweise wie „N Zeile(n) konnten nicht gelesen werden").

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
- `docs/planning/2026-07-21_asset-embeddings-auslagern.md` — Galerie-Performance, letzter
  großer Hebel (Bild-Tabelle 90,8 → 11 MB, alle Voll-Abfragen 3-5× schneller). Bereit zum
  Start, hängt an nichts.
