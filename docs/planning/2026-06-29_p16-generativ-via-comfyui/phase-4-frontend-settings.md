# Phase 4 — Frontend: Settings + Service/Store

**Rating:** standard (UI-Umbau auf bestehender Struktur, klarer Kontrakt)

## Kontext (lesen)

- [frontend/src/app/features/einstellungen/comfyui/comfyui.ts](../../../frontend/src/app/features/einstellungen/comfyui/comfyui.ts) + `.html`
- [frontend/src/app/services/comfyui.service.ts](../../../frontend/src/app/services/comfyui.service.ts)
- [frontend/src/app/store/comfyui/](../../../frontend/src/app/store/comfyui/) — actions/effects/reducer/selectors
- [frontend/src/app/models/comfyui-workflow.model.ts](../../../frontend/src/app/models/comfyui-workflow.model.ts)
- [docs/conventions/angular.md](../../../docs/conventions/angular.md), [docs/conventions/ngrx.md](../../../docs/conventions/ngrx.md)
- README → Kontrakt; [[feedback-komponenten-aufspaltung]] (Shell + Child, kein Monolith)

## Akzeptanzkriterien

1. **Modell angepasst:** `ComfyUIWorkflow` → Discovery-DTO (`key`, `category`, `inputs`,
   `prompt?`, `negativePrompt?`, `resolution?`, `mask?`, `isValid`, `errors`). `isActive`,
   `templatePath`, `validationErrors`-CRUD-Reste entfernt.
2. **Settings-Liste read-only:** Workflows werden gelistet mit Name, Kategorie-Badge, erkannten
   Inputs/Prompt/Resolution/Maske und Validitäts-Status. **Kein** Upload-Button, **keine**
   Aktivieren/Deaktivieren/Duplizieren/Löschen/Redetect-Buttons. Ein Hinweis erklärt die
   Datei-Ablage (`.photofant/workflows/`) — dezente Erklärungs-Affordance (i-Icon/Tooltip).
3. **Drei Default-Dropdowns:** je Aufgabe (Upscale / Image Edit / Inpaint) ein `<select>` über
   alle Workflows; Auswahl wird über `PUT /api/settings/comfyui` gespeichert. Optionale
   Vorfilterung nach erkannter `category`, aber jede Wahl erlaubt.
4. **Store/Service:** `loadWorkflows` = Scan-Abruf; `createWorkflow`/`activate`/`deactivate`/
   `duplicate`/`delete`/`redetect`/`update`-Actions entfernt; `loadDefaults`/`setDefaults` ergänzt.
5. **Idiotensicherheit:** Erstnutzer versteht ohne Doku, dass Workflows aus dem Ordner kommen und
   wie er die drei Aufgaben zuordnet (geprüft am Flow, nicht per Hilfetext-Pflaster).
6. `npm run lint && npm run build` grün.

## Checkliste

- [x] `comfyui-workflow.model.ts` auf Discovery-DTO umstellen (`key`, `isValid`, `errors`; `id`/`isActive`/`templatePath`/`validationErrors` raus)
- [x] `comfyui.service.ts`: `activateWorkflow`/`deactivateWorkflow`/`revalidateWorkflow` raus; `updateWorkflow`/`deleteWorkflow`/`duplicateWorkflow`/`redetectInputs` auf `key: string` umgestellt; `runWorkflow` auf `key: string`
- [x] Store: Activate/Deactivate-Actions/Effects/Reducer-Handler raus; `selectedWorkflowId: string | null`; `selectActiveWorkflows` ohne `isActive`-Filter; alle `workflow.id` → `workflow.key`
- [x] Galerie: `activeWorkflowId: signal<string | null>`, `RunFirePayload.workflowKey`, run-leiste HTML auf `wf.key`
- [ ] Settings-Liste fully read-only: Upload-, Duplizieren-, Löschen-, Redetect-Buttons entfernen; stattdessen Ordner-Hinweis (`.photofant/workflows/`)
- [ ] Drei Default-Dropdowns (Upscale / Image Edit / Inpaint) + `loadDefaults`/`setDefaults`-Actions + Backend-Endpunkte prüfen
- [ ] Komponente sauber geschnitten (Shell + Child falls zu groß, [[feedback-komponenten-aufspaltung]])
- [ ] Doc-Update: `code-map.md` (ComfyUI-Frontend-Zeile)

## Report-Back
Strukturelle Umstellung erledigt (2026-06-29): Bugfix für "aktivieren funktioniert nicht" als Einstieg in Phase 4. Model, Service, Store, run-leiste auf FS-basiertes Discovery-DTO umgestellt. Noch offen: read-only Settings-Liste, drei Default-Dropdowns.
