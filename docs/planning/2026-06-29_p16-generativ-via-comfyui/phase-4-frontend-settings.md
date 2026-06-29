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

- [ ] `comfyui-workflow.model.ts` auf Discovery-DTO umstellen
- [ ] `comfyui.service.ts`: Scan-/Defaults-Endpunkte, CRUD-Calls raus
- [ ] Store: Actions/Effects/Reducer/Selectors anpassen (Defaults rein, CRUD raus)
- [ ] `comfyui.ts`/`.html`: Liste read-only + drei Default-Dropdowns + Ordner-Hinweis
- [ ] Komponente sauber geschnitten (Shell + Child falls zu groß, [[feedback-komponenten-aufspaltung]])
- [ ] Doc-Update: `code-map.md` (ComfyUI-Frontend-Zeile)

## Report-Back
_(beim Umsetzen füllen)_
