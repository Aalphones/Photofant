# Phase 2 - Backend: Warten, Ergebnis finden, importieren

**Rating:** heikel
**Status:** complete

## Kontext

- [backend/photofant/api/comfyui.py](../../../backend/photofant/api/comfyui.py) - Run, Results, Import
- [backend/photofant/jobs/comfyui_run_job.py](../../../backend/photofant/jobs/comfyui_run_job.py) - Submit + Job-Queue
- [backend/photofant/comfyui/client.py](../../../backend/photofant/comfyui/client.py) - `/history`, `/view`
- [backend/photofant/comfyui/introspect.py](../../../backend/photofant/comfyui/introspect.py) - Save-Node-Erkennung
- [backend/photofant/comfyui/validator.py](../../../backend/photofant/comfyui/validator.py) - Workflow-Validierung
- [backend/photofant/db/models.py](../../../backend/photofant/db/models.py) - `Version`, `AssetInstance`
- [docs/conventions/python.md](../../../docs/conventions/python.md)
- [docs/conventions/testing.md](../../../docs/conventions/testing.md)

## Akzeptanzkriterien

1. Neuer Route-Handler `POST /api/comfyui/defaults/{task}/run` laedt den passenden Default-Key aus
   den ComfyUI-Settings und nutzt den bestehenden Patch-/Batch-Mechanismus.
2. Der generische Workflow-Run bleibt unveraendert Fire-and-forget.
3. `run_comfyui_run_job` oder ein neuer Wrapper kann optional:
   - `prompt_id` speichern
   - `/history/{prompt_id}` bis Output oder Timeout pollen
   - den eindeutigen Output aus der History extrahieren
   - Bildbytes via `/view` oder `output_dir` laden
   - eine neue aktuelle `Version(type="comfyui")` am `target_asset_id` anlegen
   - Thumbnails erzeugen
   - nach erfolgreichem DB-Commit die importierte lokale Output-Datei loeschen
4. Bestehende Import-Logik aus `results/import` wird nicht dupliziert, sondern in einen gemeinsamen
   Helper verschoben.
5. Batch-Zuordnung ist explizit: Anzahl `target_asset_ids` entspricht Anzahl expandierter Jobs.
6. Cleanup ist defensiv:
   - nur fuer Auto-Import, nie fuer generische Run-Leisten-Outputs
   - nur wenn `comfyui.output_dir` gesetzt ist
   - nur wenn `filename/subfolder` per Resolve-Pruefung innerhalb dieses Ordners liegt
   - nur nach erfolgreichem Import und Thumbnail-Versuch
   - Remote-only Outputs ohne lokalen Pfad werden nicht geloescht
7. Fehlerfaelle sind hart und klar:
   - kein Default gesetzt
   - ComfyUI nicht erreichbar
   - Workflow ohne eindeutigen Output
   - Timeout beim Warten auf History
   - Output-Datei nicht abrufbar
8. Tests decken mindestens ab:
   - generischer Run importiert nicht
   - Default-Run importiert bei History-Output
   - Auto-Import loescht importierte lokale Output-Datei nach erfolgreichem Import
   - Cleanup verweigert Pfade ausserhalb `output_dir`
   - mehrere unmarkierte Outputs blockieren
   - Bulk-Zielanzahl passt nicht
9. `cd backend && uv run ruff check .` und relevante Backend-Tests sind gruen.

## Checkliste

- [x] Settings-TypedDict/Defaults um Polling-Keys ergaenzen
- [x] Default-Run-DTOs und Route implementieren
- [x] Output-Auswahl aus Introspection/History implementieren
- [x] Import-Helper aus `results/import` extrahieren
- [x] Cleanup-Helper fuer importierte lokale Outputs mit Resolve-Pruefung implementieren
- [x] Job-Polling + Fortschritt + Timeout implementieren
- [x] Backend-Tests ergaenzen
- [x] `docs/models.md` nur anfassen, falls DB-/Version-Felder neu entstehen

## Report-Back

- Implementiert: `POST /api/comfyui/defaults/{task}/run` fuer `upscale|edit|inpaint`,
  Default-Key aus Settings, Output-Node-Gate, explizite `target_asset_ids`-Zuordnung.
- Auto-Import laeuft optional im bestehenden ComfyUI-Job: Prompt submitten, History pollen,
  eindeutigen Output importieren, Version-Metadaten setzen, Thumbnails erzeugen, lokalen Output
  defensiv loeschen.
- Manuelle `results/import` nutzt denselben Import-Helper; generischer `workflows/{key}/run`
  bleibt Fire-and-forget.
- Verifikation: `uv run pytest tests\test_comfyui_run.py tests\test_comfyui_import.py
  tests\test_comfyui_workflow.py tests\test_comfyui_discovery.py tests\test_comfyui_auto_import.py -q`
  -> 75 passed, 1 bestehende StarletteDeprecationWarning.
- Target-Lint: `uv run ruff check photofant\api\comfyui.py photofant\jobs\comfyui_run_job.py
  photofant\comfyui\importer.py photofant\settings.py tests\test_comfyui_run.py
  tests\test_comfyui_auto_import.py tests\test_comfyui_import.py` -> gruen.
- Full Backend-Ruff: `uv run ruff check .` bleibt rot wegen bestehender Altlasten ausserhalb der
  Phase (`alembic/versions/0020_prompt_template.py` E501, `photofant/api/assets.py` B008).
