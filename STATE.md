# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p26-recommendation-engine/`
**Phase:** 2/3 — Empfehlungs-Karten-UI (unter Lore Panel) (pending, standard)
**Nächster Schritt:** Frontend — Empfehlungs-Karten unter dem Lore-Panel in der Lightbox
rendern (Vorschaubild + Score + Reason-Checkliste). Backend ist fertig: `GET /api/recommendations?asset_id=`
liefert `{status, recommendations[]}`; bei `status:"computing"` über den SSE-Job-Stream auf den
`recommendation`-Job warten und neu laden. Details + Andock-Hinweise in `FINDINGS.md` (für Phase 2 getaggt).

## Modell-Empfehlung nächste Phase

Phase 2 ist **standard** → `sonnet` reicht (Phase 1 lief heikel auf Opus). Beim Wiedereinstieg:
`/clear`, dann `/model sonnet`, dann `/implement`.

## Phase 1 (Recommendation-Job + Reason-Chain, Backend) — fertig, committet

Empfehlungs-Engine kombiniert CLIP-Bildähnlichkeit (`db/vector_index.py`) mit dem Wissensgraph
(P22) zu einem gewichteten Score samt Begründungskette — **kein neues Modell**. Neue Module:
`recommendation/context.py` (Graph-Kontext: persons/roles/films, gebündelt aufgelöst),
`recommendation/scoring.py` (Score + Reason-Chain + Kandidatensammlung), `jobs/recommendation_job.py`
(`RecommendationJob`, idempotenter Cache-Ersatz), `api/recommendations.py`
(`GET /recommendations?asset_id=` + `.../why-not`). Neue Tabelle `recommendation_cache` (Migration 0036,
up/down grün). Settings-Block `recommendations.*`. ADR-026.

**Kern-Design:** Ein Asset hat drei domänen-agnostische Graph-Ebenen — `persons` (aktive
`asset_instance`, **ohne** `_unknown`-Sammelperson), `roles` (direkt verknüpfte Entities), `films`
(deren 1-Hop-Beziehungsziele). Score = gewichtete Summe same_person/same_role/same_film (0/1) +
clip_similarity (0..1). Default-Gewichte summieren zu 1.0 → Score in [0,1], `min_score` 0.3.

**Deviations (Details in `phase-1-recommendation-job.md`):** (1) **ein** `RecommendationJob` statt
`RecommendationJob` + `RecommendationUpdateJob` (idempotenter Ersatz bedient beides); (2) ADR-**026**
statt reservierter 012 (belegt); (3) Depth-Schutz weggelassen (Sackgassen-Job, kein Rekursionspfad).

**Qualität:** 14 neue Tests grün, volle Suite 347 passed / **13 vorbekannte** Fails unverändert
(`test_comfyui_run.py` u.a., Signatur-Drift — nicht P26), `ruff` grün auf allen neuen Dateien.
**Vorbestehend, nicht meins (🟡):** 2 `ruff`-Fehler (E501) in `jobs/comfyui_run_job.py` — außerhalb
P26-Scope, gemeldet.

## Smoke-Checkliste (du prüfst am Plan-Ende, nach Phase 3 — Details im README)

Vorab schon jetzt für Phase 1 gegen die echte Bibliothek prüfbar:
1. `curl "http://localhost:8000/api/recommendations?asset_id=<x>"` → bei erstem Aufruf `status:"computing"`,
   nach dem Job-Lauf `status:"ready"` mit ≥1 Empfehlung, deren `reasons` **CLIP + ein Graph-Signal** mischen
   (an einem Bild mit verknüpfter Person belegbar). **Wackligste Stelle:** die Scoring-Gewichte — ob die
   Rangfolge am realen Set „sinnvoll" ist, zeigt erst echtes Bildmaterial (Reason-Chain macht Fehlgewichtung sichtbar).
2. `curl ".../recommendations/<source>/<target>/why-not"` → `reasons` (anwesend) + `missing` (fehlend) + `recommended`.
3. `recommendations.enabled=false` in `settings.json` → `status:"disabled"`, keine Empfehlungen.

## Backlog (nach P26)

- `2026-07-01_p27-gemma-integration/` — KI-Layer/Gemma + Import/Update/Interview-Jobs.
- `2026-07-06_p34-mcp-wissensbasis/` — Entities/Beziehungen, Media-Links/Aufgaben, Lore/Empfehlungen,
  agentischer Workflow (braucht P24–P26 — nach P26 erfüllt).

**Offene Follow-ups aus früheren Plänen** (unverändert, nicht blockierend): siehe git-Historie/README-Archive
(P22 Embeddings-Suche, P36/P37 Smoke-Checklisten, 124 `mypy --strict`-Altfehler, kein Vollprojekt-Grün-Gate).
