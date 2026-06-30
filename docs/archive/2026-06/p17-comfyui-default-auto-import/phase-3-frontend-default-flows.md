# Phase 3 - Frontend: Default-Flows umhaengen

**Rating:** standard

## Kontext

- [frontend/src/app/services/comfyui.service.ts](../../../frontend/src/app/services/comfyui.service.ts)
- [frontend/src/app/models/comfyui-workflow.model.ts](../../../frontend/src/app/models/comfyui-workflow.model.ts)
- [frontend/src/app/store/editor/](../../../frontend/src/app/store/editor/)
- [frontend/src/app/features/editor/editor.ts](../../../frontend/src/app/features/editor/editor.ts)
- [frontend/src/app/features/editor/flux2-panel/](../../../frontend/src/app/features/editor/flux2-panel/)
- [frontend/src/app/features/editor/inpaint-panel/](../../../frontend/src/app/features/editor/inpaint-panel/)
- [frontend/src/app/features/editor/upscale-panel/](../../../frontend/src/app/features/editor/upscale-panel/)
- [frontend/src/app/features/galerie/](../../../frontend/src/app/features/galerie/) - Bulk-Upscale / Lightbox-Upscale
- [frontend/src/app/features/galerie/run-leiste/](../../../frontend/src/app/features/galerie/run-leiste/) - muss Fire-and-forget bleiben
- [docs/conventions/angular.md](../../../docs/conventions/angular.md)
- [docs/conventions/typescript.md](../../../docs/conventions/typescript.md)

## Akzeptanzkriterien

1. Editor-Upscale, Image Edit und Inpaint rufen den neuen Default-Run-Endpunkt mit
   `target_asset_ids` auf.
2. Galerie-Bulk-Upscale uebergibt alle markierten Assets als `target_asset_ids` und erhaelt pro Asset
   einen Job.
3. Lightbox-/Einzel-Upscale nutzt denselben Default-Pfad.
4. Nach Job-Fertigstellung refreshen Galerie/Editor die betroffenen Asset-/Version-Daten, sodass das
   importierte Ergebnis sichtbar wird.
5. Die Run-Leiste nutzt weiterhin `runWorkflow(key, payload)` gegen `/workflows/{key}/run`; dort gibt
   es keinen Auto-Import-Schalter und keine versteckte Target-Asset-Logik.
6. UI-Fehler sind fuer Erstnutzer eindeutig: kein Default gesetzt, Workflow-Output mehrdeutig,
   ComfyUI-Timeout.
7. `cd frontend && npm run lint && npm run build` ist gruen.

## Checkliste

- [x] `comfyui.service.ts`: `runDefaultWorkflow(task, payload)` ergaenzen
- [x] Frontend-Modelle fuer Default-Run-Request/Response ergaenzen (`DefaultRunTask`, `DefaultRunRequest`, `comfyui_run` in JOB_KINDS)
- [x] Editor-Store/Effects auf Default-Run umstellen (`task` statt `workflowKey`, Effect ruft `runDefaultWorkflow`)
- [x] Upscale/Edit/Inpaint-Panels unveraendert; `dispatchGenerative` in editor.ts baut `target_asset_ids: [targetId]`
- [x] Galerie-Bulk und Lightbox-Einzelupscale auf Default-Run umstellen
- [x] Run-Leiste explizit unveraendert — ruft weiterhin `runWorkflow` (kein Auto-Import)
- [x] Relevante Docs (`docs/code-map.md`) synchronisiert; `docs/routes.md` war bereits aktuell

## Report-Back

Alle Default-Aktionen (Editor Edit/Inpaint/Upscale, Lightbox-Upscale, Galerie-Bulk-Upscale)
rufen POST /api/comfyui/defaults/{task}/run auf. Die Run-Leiste bleibt Fire-and-forget.

Lightbox-Refresh: pendingUpscaleJobId signal + effect beobachtet allJobs aus dem SSE-Store;
bei state=done wird reloadTrigger gebumpt, bei state=error upscaleError gesetzt.

Commit: ae8b302
