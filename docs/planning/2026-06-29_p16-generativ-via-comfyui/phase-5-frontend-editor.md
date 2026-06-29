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

- [ ] `editor.ts`: `activeTool` um `upscale`; Gating über Defaults statt capabilities
- [ ] `flux2-panel` → Edit-Panel verschlanken (Prompt + optional Resolution)
- [ ] `inpaint-panel`: Masken-DataURL an Run durchreichen (+ Prompt)
- [ ] Upscale-Panel (neu, minimal)
- [ ] Editor-Store: `fluxEdit`/`inpaint`-Effekte → `comfyui`-Run
- [ ] `generative.service.ts` löschen + Referenzen
- [ ] `run-leiste`: Prompt-/Resolution-Felder + Payload
- [ ] Galerie/Lightbox: Bulk-Upscale-Aktion
- [ ] Doc-Update: `code-map.md` (Editor/Generativ-Zeile), `design-reconciliation.md` (Mockup-Diskrepanz)

## Report-Back
_(beim Umsetzen füllen)_
