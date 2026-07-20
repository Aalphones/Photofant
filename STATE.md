# STATE

**Aktiver Plan:** `docs/planning/2026-07-20_recommendation-cache-invalidation/`
**Phase:** 4/4 — Clustering (pending)
**Nächster Schritt:** Phase 4 umsetzen (automatische Zuordnung nach Import invalidiert Empfehlungen — siehe `phase-4-clustering.md`, vermutlicher Hauptverursacher der Cache-Staleness).

## Phase 3 erledigt (Wissensgraph-Verknüpfungen)

Alle 7 Call-Sites (persons/assets link-entity, knowledge relationships/update/delete,
knowledge-patch-job) invalidieren jetzt vor ihrem Commit — `assets_of_persons`/
`assets_for_entity` aus Phase 1 wiederverwendet, `knowledge/service.py` bleibt
unangetastet. Neue Testdatei `test_recommendation_invalidation_knowledge.py` (5 Tests,
grün). ruff/mypy: keine neuen Fehler. Details: `phase-3-wissensgraph.md` (Report-Back).

## Phase 2 erledigt (Manuelle Face-/Person-Aktionen)

Alle 9 Call-Sites (faces/assets/persons/review-queue/bulk-assign) invalidieren jetzt vor ihrem
Commit. Nebenbei `split_faces`/`delete_person` in `person_folders.py` von losen Dicts auf
`TypedDict` umgestellt (5 vorbestehende mypy-Fehler dabei mitbehoben). Neue Testdatei
`test_recommendation_invalidation_manual.py` (6 Tests, grün). ruff grün, mypy keine neuen
Fehler, 46/46 relevante Tests grün. Details: `phase-2-manuelle-aktionen.md` (Report-Back).

## Vorheriger Stand (P35 abgeschlossen)

P35 (Gemma-GGUF-Runtime) alle 3 Phasen ✅ complete, archiviert nach
`docs/archive/2026-07/2026-07-20_p35-gemma-gguf-runtime/`.

## Smoke-Test P35 ausstehend (User)

GGUF-Gemma-Runtime real prüfen (CUDA-Wheel, VRAM-Wechsel, Chat-Template, Idle-Unload,
Manifest-Bind, mmproj) — Checkliste (Wackelstellen zuerst):
`docs/archive/2026-07/2026-07-20_p35-gemma-gguf-runtime/README.md`.

## Backlog — Lightbox-Smoke ausstehend (User)

Plan archiviert (`docs/archive/2026-07/2026-07-20_lightbox-tabbed-panel.md`), Smoke-Checkliste
steht dort (Wackelstellen zuerst). User schaut sich das später separat an, kein Implementier-Follow-up nötig, außer er meldet Befunde zurück.

## Phase 1 erledigt (GGUF-Runtime + Adapter + VRAM-Koordination)

`inference/gguf_engine.py` neu (`GgufEngine`, Lifecycle-Form gespiegelt von
`GenerativeEngine`), `inference/adapters/gemma_gguf.py` neu (`GemmaGgufAdapter` +
`GemmaGgufVisionAdapter` — zwei Klassen statt Instanz-Flag, Begründung in der
Phasen-Datei), `VisionTextGenerator`-Protocol in `interfaces.py`, Cross-Unload in
beide Richtungen (`generative_engine.py` ↔ `gguf_engine.py`, ADR-029), Idle-Loop +
Shutdown in `main.py` um den GGUF-Slot erweitert, neue Extra-Group `gemma-gguf` in
`pyproject.toml`. ruff grün (neue/geänderte Dateien), mypy grün bis auf den
erwarteten `llama_cpp`-Import-Fehler (Paket noch nicht installiert — Smoke #1
installiert es). ADR-029 angelegt. **Noch offen: Backlog P27-Smoke + Archivieren**
(siehe unten) — unabhängig von P35, wartet weiter auf den User.

## Backlog — P27 (parkt, nicht blockierend für P35)

Plan `docs/planning/2026-07-01_p27-gemma-integration/` — alle 4 Phasen ✅ complete,
Plan-Ende offen: (1) User-Smoke (Checkliste in der README, Wackelstellen zuerst) —
Gemma muss dafür geladen/verfügbar sein; (2) Archivieren nach grünem Smoke
(`git mv` → `docs/archive/2026-07/`, README-Bottom-Sektionen füllen).

## Backlog (nach P35)

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan + P27 stehen.

## Smoke-Test P26 ausstehend (User)

Real-Check der Empfehlungs-Engine — Details:
`docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`.
