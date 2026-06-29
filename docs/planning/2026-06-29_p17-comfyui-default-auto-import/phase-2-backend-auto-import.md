# Phase 2 - Backend: Warten, Ergebnis finden, importieren

**Rating:** heikel

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

- [ ] Settings-TypedDict/Defaults um Polling-Keys ergaenzen
- [ ] Default-Run-DTOs und Route implementieren
- [ ] Output-Auswahl aus Introspection/History implementieren
- [ ] Import-Helper aus `results/import` extrahieren
- [ ] Cleanup-Helper fuer importierte lokale Outputs mit Resolve-Pruefung implementieren
- [ ] Job-Polling + Fortschritt + Timeout implementieren
- [ ] Backend-Tests ergaenzen
- [ ] `docs/models.md` nur anfassen, falls DB-/Version-Felder neu entstehen

## Report-Back

Noch offen.
