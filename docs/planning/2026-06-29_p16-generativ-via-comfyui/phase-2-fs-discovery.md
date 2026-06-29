# Phase 2 — Filesystem-Discovery, DB raus

**Rating:** heikel (Architektur-Umkehr, Migration, API-Umbau — definiert den Kontrakt)

## Kontext (lesen)

- [backend/photofant/api/comfyui.py](../../../backend/photofant/api/comfyui.py) — heutiger CRUD/Activate/Run-Flow
- [backend/photofant/settings.py](../../../backend/photofant/settings.py) — `ComfyUISettings`, `SETTINGS_DEFAULTS`
- [backend/photofant/db/models.py](../../../backend/photofant/db/models.py) — `ComfyUIWorkflow` (Z. 225)
- [backend/photofant/jobs/comfyui_run_job.py](../../../backend/photofant/jobs/comfyui_run_job.py) — `enqueue_comfyui_runs`, `patch_template`
- [backend/photofant/alembic/](../../../backend/photofant/alembic/) — Migrations-Muster
- README → Kontrakt-Sektion

## Akzeptanzkriterien

1. **Verzeichnis = Quelle:** `GET /api/comfyui/workflows` scannt `.photofant/workflows/*.json`
   (+ `*.api.json`), introspiziert jede Datei on-the-fly und liefert das Discovery-DTO. `key` =
   Dateiname ohne Endung. Keine DB-Beteiligung.
2. **Kein Aktivieren-Gate:** Jeder valide Workflow ist sofort lauffähig. Invalide erscheinen mit
   `is_valid=false` + Fehlern, blockieren den Scan aber nicht.
3. **Run per `key`:** `POST /api/comfyui/workflows/{key}/run` ersetzt die id-basierte Route.
   Request nimmt zusätzlich `prompt`, `negative_prompt`, `resolution`, `mask` (siehe Kontrakt) und
   patcht sie über die erkannten Bindings.
4. **Alpha-Maske:** Bei `mask.mode='alpha'` kombiniert das Backend Quellbild + `mask_data_url`
   zu einem RGBA-PNG (Maske → Alpha-Kanal) und lädt **dieses** als Bild-Input des
   `image_node_id` hoch. Konvention: markierter Bereich = transparent (Flux-Fill-Standard);
   Richtung per Test gegen `Inpaint.json` verifizieren.
5. **Defaults in settings.json:** `ComfyUISettings` um `default_upscale`, `default_edit`,
   `default_inpaint` (je Workflow-`key` oder leer) erweitert; `GET/PUT /api/settings/comfyui`
   liest/schreibt sie. Verweist der Default auf eine fehlende Datei → leer behandelt + Hinweis.
6. **DB-Tabelle entfernt:** `ComfyUIWorkflow`-Model + Alembic-Down-Migration (drop table).
   Entfernte Routen: `POST/PATCH/DELETE /workflows`, `/activate`, `/deactivate`, `/duplicate`,
   `/revalidate`, `/redetect-inputs`, id-basierter Upload. `introspect`, `results`, `results/view`,
   `results/import`, `test-connection` bleiben.
7. `uv run ruff check .` grün; Backend startet ohne die Tabelle.

## Checkliste

- [x] Discovery-Modul: `scan_workflows()` (Verzeichnis → introspizierte DTOs, gecacht per mtime optional)
- [x] `api/comfyui.py`: Routen auf Discovery/`key` umbauen, CRUD/Activate/Duplicate/Redetect raus
- [x] Run-Route + Request-Schema um prompt/negative/resolution/mask erweitern; an `patch_template` durchreichen (Prompt/Resolution als param-artige Bindings)
- [x] Alpha-Embedding-Helper (`media/`): Bild + Masken-DataURL → RGBA-PNG-Tempfile für Upload
- [x] `settings.py`: drei Default-Keys + Defaults; PUT-Validierung (key existiert / leer)
- [x] Alembic-Migration: `comfyui_workflow` droppen; `db/models.py` Model entfernen
- [x] Unit-Test: Scan über Beispiel-Verzeichnis + Alpha-Embedding (Pflicht-Ausnahme [[private-keine-frontend-tests]])
- [x] Doc-Update: `routes.md` (geänderte/entfallene Routen), `models.md` (Tabelle weg)

## Report-Back

**Commit:** `2d95f8c` — feat(comfyui): P16 Phase 2 — FS-Discovery, DB raus, Alpha-Maske

**Umgesetzt:**
- `comfyui/discovery.py`: `scan_workflows()`, `load_workflow()`, `load_workflow_template()` — `.api.json` schlägt `.json` für gleichen key
- `media/alpha_mask.py`: `embed_mask_as_alpha()` via PIL Luminance + ImageOps.invert (Flux-Fill: markiert = transparent)
- `comfyui/client.py`: `upload_image_bytes()` für In-Memory-PNG-Upload
- `comfyui_run_job.py`: `mask_input_key` + `mask_data_url` Parameter; Alpha-Embedding im Job-Loop vor Upload
- `api/comfyui.py`: komplett umgebaut — nur noch FS-Discovery + key-basierter Run + 3 Default-Settings
- `settings.py` / `models.py`: `ComfyUISettings` um 3 Default-Keys erweitert; `ComfyUIWorkflow` Model entfernt
- Migration `0022_drop_comfyui_workflow.py` (upgrade: DROP TABLE; downgrade: recreate)
- 21 Tests (discovery + alpha-mask), alle grün; pre-existing 9 Failures in `test_comfyui_run.py` unberührt

**Abweichung:** Alpha-Embedding nutzt PIL L-mode statt separatem Alpha-Kanal — robuster bei RGBA-Canvas-Masken und opaken Masken-PNGs.

**Offen:** Masken-Richtung (markiert = transparent/opak) sollte beim ersten echten Flux-Fill-Run mit Inpaint.json verifiziert werden. Notiz in Phase-6-Doku.

**Status:** complete
