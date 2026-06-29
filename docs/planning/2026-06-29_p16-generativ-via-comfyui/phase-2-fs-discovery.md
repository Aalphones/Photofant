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

- [ ] Discovery-Modul: `scan_workflows()` (Verzeichnis → introspizierte DTOs, gecacht per mtime optional)
- [ ] `api/comfyui.py`: Routen auf Discovery/`key` umbauen, CRUD/Activate/Duplicate/Redetect raus
- [ ] Run-Route + Request-Schema um prompt/negative/resolution/mask erweitern; an `patch_template` durchreichen (Prompt/Resolution als param-artige Bindings)
- [ ] Alpha-Embedding-Helper (`media/`): Bild + Masken-DataURL → RGBA-PNG-Tempfile für Upload
- [ ] `settings.py`: drei Default-Keys + Defaults; PUT-Validierung (key existiert / leer)
- [ ] Alembic-Migration: `comfyui_workflow` droppen; `db/models.py` Model entfernen
- [ ] Unit-Test: Scan über Beispiel-Verzeichnis + Alpha-Embedding (Pflicht-Ausnahme [[private-keine-frontend-tests]])
- [ ] Doc-Update: `routes.md` (geänderte/entfallene Routen), `models.md` (Tabelle weg)

## Report-Back
_(beim Umsetzen füllen)_
