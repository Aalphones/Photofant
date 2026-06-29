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

- [ ] `comfyui.service.ts`: `runDefaultWorkflow(task, payload)` ergaenzen
- [ ] Frontend-Modelle fuer Default-Run-Request/Response ergaenzen
- [ ] Editor-Store/Effects auf Default-Run umstellen
- [ ] Upscale/Edit/Inpaint-Panels Payloads mit `target_asset_ids` bauen lassen
- [ ] Galerie-Bulk und Lightbox-Einzelupscale auf Default-Run umstellen
- [ ] Run-Leiste explizit unveraendert lassen und ggf. Test/Code-Kommentar fuer Trennung setzen
- [ ] Relevante Docs (`docs/routes.md`, `docs/code-map.md`, `docs/design-reconciliation.md` falls noetig) final synchronisieren

## Report-Back

Noch offen.
