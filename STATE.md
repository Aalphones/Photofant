# STATE

**Aktiver Plan:** `docs/planning/2026-07-01_p25-lore-panel/`
**Phase:** 3/3 — Korrektur-Flow (PatchJob) (pending) — **standard**
**Nächster Schritt:** `phase-3-correction-flow.md` umsetzen: `POST /entities/{id}/patch` →
`jobs/knowledge_patch_job.py` → `update_entity(owner=user)` → Markdown+Cache, Explainability-Eintrag;
im Lore-Panel „Das stimmt nicht"-Aktion + Korrektur-Formular. Danach ist P25 (und damit das MVP) durch.
Modell-Hinweis: Phase ist „standard" — `/clear`, dann `/model sonnet` reicht.

**Phase 2 (Lore-Panel-UI, Lightbox) ist fertig, committet:**
Neue Komponente `features/galerie/lightbox/lore-panel/` (`pf-lore-panel`) dockt als weitere
`.panel-sec` nach dem Panel-Header an P15s Lightbox an (beide Modi: Asset via `asset_id`,
Gesichter-Modus via `person_id` der Face-Person). Rendert das Wissen als **5 domänen-agnostische
Sektionen** (Kurzbio · Beziehungen · Franchises · Eigene Bilder · Quellen) — **Deviation** von der
7-Sektionen-Liste aus Dok 050 §5 (Sascha 2026-07-09, Doku in `docs/design-reconciliation.md`):
„Rollen"/„Verwandte Entitäten" haben kein eigenes Datenfeld, ihre Info steckt in „Beziehungen".
Lore lädt lokal per `toSignal` + neuem `KnowledgeService.getLore({assetId|personId})` (nach
P15-Nachbar-Muster `detail`/`lineage`/`relatedRail`, kein NgRx-Slice). Leer-Zustand „anlegen"
(nur bei Personenkontext) → `/wissen`; Beziehungs-/Franchise-Klick → `/wissen?entity=` (unaufgelöste
Ziele mit leerem Typ nicht klickbar). `models/knowledge.model.ts`: `LoreDto` auf Vollform +
`ResolvedRelationshipDto`/`MediaRefDto`. Frontend `tsc`+`ng build` grün.
**Nebenbei gefixt (Phase-1-Backend-Bug, mit Sascha abgestimmt):** Personen-Thumbnail in `get_lore`
kam als `/faces/{id}/thumbnail` (ohne `/api`) → Bild lud nicht; auf `/api/faces/{id}/thumbnail`
gezogen (`api/knowledge.py`) + Test-Assertion (`test_knowledge_api.py:319`) nachgezogen.
Backend-Knowledge-Tests grün (50).
**Findings Phase 2 (alle in FINDINGS.md abgehakt):** Franchise-Dedup über ids statt Typ-String;
unaufgelöste Beziehungsziele (`type==""`) nicht navigierbar; portraitlose Personen fehlen erwartbar
in „Eigene Bilder".
**Follow-up P25/P26:** `related_media`-Thumbnails sind bewusst noch nicht klickbar (Anzeige-only);
Entity-Detail-Ansicht existiert weiter nicht — der `?entity=`-Param landet auf der `/wissen`-Übersicht,
nicht bei der Entity selbst (bekannt aus P24, wird eigenständig behandelt).

**Phase 1 (Lore-Aggregations-API, Backend) ist fertig, committet (`c51c572`):**
`get_lore()` liefert jetzt die Vollform (Beziehungsziele zu Titel/Typ aufgelöst, Franchises
als eigenes Feld, media_links zu Thumbnail-Refs gejoint via `_resolve_media_refs` in
`api/knowledge.py`). Neue Route `GET /api/knowledge/lore?asset_id=/person_id=` → 200 mit
`entity: null` ohne Verknüpfung (nie 404 — Kontrakt). Backend-Tests grün (50 in
`test_knowledge_service.py`/`test_knowledge_api.py`), volle Suite unverändert 13
vorbekannte Fails, `ruff` grün.
**Findings für Phase 2** (`FINDINGS.md`): `franchises[]` dedupliziert nicht gegen
`relationships[]` (UI muss Franchise-Ziele beim Rendern von „Beziehungen" selbst
rausfiltern) · Personen ohne Portrait fehlen in `related_media[]` (kein Fehler, aber
„Verknüpfung da, Bild fehlt" ist erwartbar) · unbekannte Beziehungsziele kommen mit
`target.type == ""` zurück (Klick-Handling muss das abfangen).

**P24 — Photofant-Integration ist fertig (alle 3 Phasen archiviert):**
Entity-Chip auf Personen-Karte (`features/personen/person-card/`, Frosted-
Glass-Stil wie die bestehende „Neue Person"-Affordance) und im Bild-Detail
(`features/galerie/lightbox/`, `.tag-chip`-Stil), beide klickbar → `/wissen?entity=<id>`.
`models/person.model.ts` + `models/asset.model.ts` um `linked_entity` (`EntityRefDto`) ergänzt.
Frontend-Typecheck (`npm run lint`) + `ng build` grün.
**Finding für P25** (`FINDINGS.md`): es gibt noch keine Entity-Detail-Ansicht im Frontend — nur
die allgemeine `/wissen`-Übersicht. Die Chips verlinken vorbereitend auf `/wissen?entity=<id>`;
P25 (Lore-Panel) muss den Query-Param auswerten, damit der Klick wirklich bei der Entity landet.

Phase 2 („Neue Person erkannt"-Affordance) ist fertig: Inline-Banner auf der Personen-Karte,
gespeist aus `store/knowledge`-Tasks, Wizard aus P23 wiederverwendet.

Phase 1 (Entity-Linking + Job-Kette, Backend) ist fertig, `pytest`/`ruff` grün (368 passed,
13 vorbekannte Failures unverändert). Abweichungen vom Plan-Text dokumentiert in
`docs/archive/2026-07/2026-07-01_p24-photofant-integration/FINDINGS.md` + `docs/decisions/014-…md`
(kein `ParentJobId`/`Depth`-Schleifenschutz gebaut — YAGNI, mit Nutzer abgestimmt; ADR-Nummer
011 war schon belegt).

Andere freigegebene, geparkte Pläne in `docs/planning/` (nach P24):
- `2026-07-01_p25-lore-panel/` — Lore-API + Panel-UI + Korrektur-Flow (braucht P24)
- `2026-07-01_p26-recommendation-engine/` — Empfehlungs-Job + Cards + Explainability (braucht P25)
- `2026-07-01_p27-gemma-integration/` — KI-Layer/Gemma-Adapter + Import/Update/Interview-Jobs (braucht P25)
- `2026-07-06_p34-mcp-wissensbasis/` — Entities/Beziehungen, Media-Links/Aufgaben, Lore/Empfehlungen, agentischer Workflow (braucht MCP-Basisplan + P24-P26)

P23–P27 lesen den P22-Kontrakt (README-Sektion „Kontrakt", jetzt im Archiv) als Single Source.

**Offene Follow-ups (🟡, nicht blockierend):**
- P22: Markdown-Embeddings / semantische Wissenssuche (bewusst nach hinten) · Relationship-Metadaten
  falls P26 es braucht · inkrementeller Reconcile mit `synced_at`-Spalte erst wenn der Vault groß wird.
- Text-Semantiksuche-Umschalter smoke-testen — Checkliste in
  `docs/archive/2026-07/2026-07-07_p36-reverse-image-search/phase-4-text-semantiksuche.md`.
- `AssetService.setAssetOriginal()` + `PATCH /assets/{id}/original` ohne Aufrufer (aus P36).
- `POST /api/search/semantic`s `query`-Zweig ist totes Backend-Duplikat (aus P36).
- P37-Smoke-Checklisten #1 (Rerank-Qualität) + #2 (Dupe-Schwellwert-Kalibrierung) stehen aus —
  Nutzer-Aufgabe am realen Bild-Set, siehe archiviertes P37-README.
- Ohne aktives DINOv2-Modell läuft kein automatischer Duplikat-Check mehr beim Import (ADR-024).
- 13 vorbestehende Test-Failures in `test_comfyui_run.py`/`test_comfyui_auto_import.py`/
  `test_caption_config.py` (Signatur-Drift `run_comfyui_run_job` fehlt `job_version_inputs`).
- 124 vorbestehende `mypy --strict`-Fehler quer über die Codebase — kein Vollprojekt-Grün-Gate aktiv.

**Smoke-Checkliste P23 (noch vom Nutzer zu prüfen — Details im archivierten P23-README):**
1. „Wissen" in der Nav öffnen → Wizard → Entity anlegen → Datei liegt im Vault.
2. Aufgabe per `curl POST .../tasks` anlegen → erscheint in der Work-Queue.
3. Aufgabe „Erledigen" → Wizard vorbelegt → speichern → Aufgabe verschwindet.
4. Zweiter Lookup zum selben Kontext → keine zweite Aufgabe.

**Smoke-Checkliste P24 (noch vom Nutzer zu prüfen — Plan-README hat die Details):**
1. `curl -X POST /api/persons/{id}/link-entity -d '{"entity_id":"..."}'` → Personen-Detail
   zeigt `linked_entity`, überlebt einen Neustart.
2. Eine Person ohne Entity bestätigen → **genau eine** offene Aufgabe entsteht, keine
   Job-Endlosschleife (Job-Dock beobachten). **Das ist die wackligste Stelle des Plans** —
   Depth-Schutz existiert nicht, nur `TaskService`-Dedup (ADR-014); hier lohnt der genaueste Blick.
3. Neue Person im Review → Hinweis „Wissen anlegen" → Wizard → danach verknüpft, Hinweis weg.
4. Personen-Karte zeigt den Entity-Chip, Klick landet auf `/wissen`. Bild-Detail (Lightbox)
   zeigt den Chip in den Metadaten, Klick schließt die Lightbox und landet ebenfalls auf
   `/wissen`. **Bekannt:** landet noch nicht bei der Entity selbst (P25-Follow-up).
