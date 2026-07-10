# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p26-recommendation-engine/`
**Phase:** 3/3 — Explainability „Warum?/Warum nicht?" (pending, standard)
**Nächster Schritt:** Backend ist fertig: `GET /api/recommendations/{source}/{target}/why-not` liefert
`{score, threshold, recommended, reasons[], missing[]}`. Phase 3 ist v.a. UI: ein „Warum?"-Popover an
jeder Empfehlungs-Karte (zeigt die schon vorhandene Reason-Chain der Karte — Signale/Confidence/Job)
und ein „Warum nicht?"-Weg an einem nicht empfohlenen Bild (ruft `why-not` live ab, zeigt anwesende +
fehlende Signale gegen die Schwelle). Details in `FINDINGS.md` (für Phase 3 getaggt).

## Modell-Empfehlung nächste Phase

Phase 3 ist **standard** → `sonnet` reicht. Beim Wiedereinstieg: `/clear`, dann `/model sonnet`,
dann `/implement`.

## Phase 2 (Empfehlungs-Karten-UI, Frontend) — fertig, ungecommittet bei Session-Ende der Vorphase, jetzt zu committen

Empfehlungs-Karten docken direkt unter dem Lore-Panel (P25) an — **keine neue Komponente**: die
generische `related-rail/` (P36, `{assetId, score, reasons}`) wird mit befüllter Begründungskette
wiederverwendet. Neue Dateien: `models/recommendation.model.ts` (`RecommendationDto`,
`recommendationReasonLabel()` — mappt Backend-Signale auf „✓ gleiche Person (…)" etc.),
`services/recommendation.service.ts` (`getRecommendations`). Geänderte Dateien: `lightbox.ts`/`.html`
(neues `recommendations`-Signal an derselben Reload-Pipeline wie `detail`/`lineage`/`relatedRail`,
Job-Wait über den globalen Job-Store statt Job-Id-Filter — Details unten), `related-rail.ts`/`.html`/`.scss`
(`loadingMessage`-Input, Reasons-Liste ohne Bullet-Punkt), `models/job.model.ts` (`JOB_KINDS` +
`'recommendation'`).

**Deviation (Details in `phase-2-recommendation-cards.md`):** Kein Job-Id-Filter beim Warten auf
den Job — der Endpoint liefert bei Cache-Miss keine Job-Id. Stattdessen: `effect()` beobachtet den
globalen `jobsSelectors.allJobs`-Store auf einen `kind:"recommendation"`-Job in `done`/`error`,
während die UI noch auf „computing" steht, dann Reload (selbstkorrigierend bei Fehltreffer).

**Reco-State bewusst komponentenlokal** (nicht `store/gallery/`/`store/knowledge/`) — konsistent zu
P25 (Lore-Panel) und P36 (Related-Rail), die ihre Pro-Asset-Daten ebenfalls nicht in NgRx halten.

**Qualität:** `tsc --noEmit` (App + Lib) grün, `ng build` grün (keine neuen Template-/Typfehler;
Bundle-Budget-Warnungen sind Bestand, nicht durch diese Phase verursacht). Kein Live-Smoke-Test
gegen die echte Bibliothek gelaufen (privates Profil — Build/Typecheck reicht, du prüfst live).

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

1. `curl "http://localhost:8000/api/recommendations?asset_id=<x>"` → bei erstem Aufruf `status:"computing"`,
   nach dem Job-Lauf `status:"ready"` mit ≥1 Empfehlung, deren `reasons` **CLIP + ein Graph-Signal** mischen
   (an einem Bild mit verknüpfter Person belegbar). **Wackligste Stelle:** die Scoring-Gewichte — ob die
   Rangfolge am realen Set „sinnvoll" ist, zeigt erst echtes Bildmaterial (Reason-Chain macht Fehlgewichtung sichtbar).
2. Bild öffnen → unter dem Lore-Panel erscheinen Karten mit Score-Badge + „✓"-Begründungszeilen;
   Karte anklicken öffnet das Bild. **Wackligste Stelle Phase 2:** der Job-Wait ohne Job-Id — bei
   parallel laufenden Empfehlungs-Jobs für andere Bilder kann ein Reload zu früh/zu spät kommen
   (selbstkorrigierend, aber am realen Gerät noch nicht beobachtet).
3. `curl ".../recommendations/<source>/<target>/why-not"` → `reasons` (anwesend) + `missing` (fehlend) + `recommended`.
4. `recommendations.enabled=false` in `settings.json` → `status:"disabled"`, keine Empfehlungen (Karten-Bereich entfällt).

## Backlog (nach P26)

- `2026-07-01_p27-gemma-integration/` — KI-Layer/Gemma + Import/Update/Interview-Jobs.
- `2026-07-06_p34-mcp-wissensbasis/` — Entities/Beziehungen, Media-Links/Aufgaben, Lore/Empfehlungen,
  agentischer Workflow (braucht P24–P26 — nach P26 erfüllt).

**Offene Follow-ups aus früheren Plänen** (unverändert, nicht blockierend): siehe git-Historie/README-Archive
(P22 Embeddings-Suche, P36/P37 Smoke-Checklisten, 124 `mypy --strict`-Altfehler, kein Vollprojekt-Grün-Gate).
