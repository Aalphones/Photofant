# Phase 5 — Frontend: Editor-Aufgaben + Run-Leiste + Bulk

**Rating:** heikel (Maskenfluss, P9-Entkopplung, Design-Entscheidung)

## Kontext (lesen)

- [frontend/src/app/features/editor/editor.ts](../../../frontend/src/app/features/editor/editor.ts) + `.html`
- [frontend/src/app/features/editor/flux2-panel/](../../../frontend/src/app/features/editor/flux2-panel/), [inpaint-panel/](../../../frontend/src/app/features/editor/inpaint-panel/), [mask-overlay/](../../../frontend/src/app/features/editor/mask-overlay/)
- [frontend/src/app/store/editor/](../../../frontend/src/app/store/editor/) — `fluxEdit`/`inpaint`-Actions/Effects
- [frontend/src/app/services/generative.service.ts](../../../frontend/src/app/services/generative.service.ts) — entfällt
- [frontend/src/app/features/galerie/run-leiste/run-leiste.ts](../../../frontend/src/app/features/galerie/run-leiste/run-leiste.ts)
- [docs/design/js/editor-tools.jsx](../../../docs/design/js/editor-tools.jsx) — **überholtes** Mockup (siehe 🔴 README)
- README → Kontrakt + 🔴-Entscheidung

## Voraussetzung

🔴 **Panel-Schlankheit aus der README** muss entschieden sein (Default: schlanke Panels). Die AK
unten setzen die Empfehlung um; bei Gegenentscheidung AK anpassen.

## Akzeptanzkriterien

1. **Image Edit (ex `flux2-panel`):** Prompt-Eingabe; feuert den `default_edit`-Workflow via
   `run` mit `prompt`. Keine strength/steps/guidance/seed-Regler (leben im Workflow). Erkennt der
   Workflow eine Resolution → Megapixel-Feld + Aspect-Auswahl (Template-Default), sonst ausgeblendet.
2. **Inpaint (ex `inpaint-panel`):** Pinsel/Maske (bestehendes `mask-overlay`) + optionaler Prompt;
   feuert `default_inpaint` mit `mask` (asset_id + Masken-DataURL) und `prompt`. Backend bettet
   Alpha ein (Phase 2). Button disabled ohne Maske.
3. **Upscale (neu, schlank):** 1-Klick-Tool, feuert `default_upscale`; Resolution-Feld nur falls
   der Workflow einen ResolutionSelector hat. Kein Modell-/Tile-Regler.
4. **Default-Gating:** Ist für eine Aufgabe kein Default-Workflow gesetzt (oder ComfyUI aus/nicht
   erreichbar), ist das Tool deaktiviert mit klarem Hinweis + Link in die Einstellungen — statt
   der entfernten `capabilities.flux_edit/inpaint`.
5. **Galerie-Bulk-Upscale:** Aktion auf der Auswahl (bzw. Lightbox-Menü) feuert `default_upscale`
   als Batch über alle markierten Assets (bestehende Batch-Achse im Run-Job).
6. **Generische Run-Leiste erweitert:** zusätzlich zu Bild-Slots ein Prompt-Feld (falls Workflow
   `prompt` hat) und Resolution-Felder (falls `resolution`); `fire`-Payload füllt `params`/`prompt`/
   `resolution` statt heute leerem `params: {}`.
7. **P9-Reste raus:** `generative.service.ts` entfernt; Editor-Store `fluxEdit`/`inpaint`-Actions
   auf ComfyUI-Run umgestellt; `capabilities`-Nutzung im Editor ersetzt.
8. Erkennbar bedienbar für Erstnutzer (Idiotensicherheits-Gate); `npm run lint && npm run build` grün.

## Checkliste

- [x] `editor.ts`: `activeTool` um `upscale`; Gating über Defaults statt capabilities
- [x] `flux2-panel` → Edit-Panel verschlanken (Prompt + optional Resolution)
- [x] `inpaint-panel`: Masken-DataURL an Run durchreichen (+ Prompt)
- [x] Upscale-Panel (neu, minimal)
- [x] Editor-Store: `fluxEdit`/`inpaint`-Effekte → `comfyui`-Run (`runGenerative`)
- [x] `generative.service.ts` löschen + Referenzen
- [x] `run-leiste`: Prompt-/Resolution-Felder + Payload
- [x] Galerie/Lightbox: Bulk-Upscale-Aktion (BulkBar + Lightbox-Einzelupscale)
- [x] Doc-Update: `code-map.md` (Editor/Generativ-Zeile), `design-reconciliation.md` (Mockup-Diskrepanz)

## Report-Back

**Status:** complete (2026-06-29).

Kontrakt-Lücke beim Start gefunden: Frontend-Workflow-Modell war veraltet (kein prompt/resolution/mask,
stattdessen ein totes `params`-Feld) — auf den echten Backend-Kontrakt gezogen (Mapper + `runWorkflow`).
Geteilte `resolution-field`-Komponente für die drei Panels. Generative Tools laufen jetzt über ein
einheitliches `editorActions.runGenerative` → `comfyui.service.runWorkflow`. Default-Gating zeigt einen
Hinweis + Einstellungen-Link, wenn ComfyUI aus oder kein Default-Workflow gesetzt ist. Lightbox-Upscale
hing noch am gelöschten P9-Endpoint — auf `default_upscale` umgestellt; Bulk-Upscale neu in der
Auswahl-Leiste. `CapabilitiesDto` (FE) um die toten upscale/flux_edit/inpaint-Felder bereinigt.
`npm run lint` (tsc) grün, `npm run build` grün (nur vorbestehende Bundle-Budget-Warnungen).

**Bewusste Abweichungen:** Inpaint-Prompt optional (Maske allein genügt zum Feuern). Run-Leiste-Prompt
als einzeilige Eingabe (Platz), Editor-Edit-Prompt als Textarea.
