# P16 — Generativ läuft über ComfyUI

**Status:** Entwurf (zur Freigabe) · angelegt 2026-06-29
**ADR:** 008 (ersetzt ADR-002 „diffusers in-process", erweitert ADR-003 „ComfyUI-Trigger")

## Ziel

Die drei generativen Bild-Aufgaben **Upscale, Image Edit, Inpaint** laufen ausschließlich
über ComfyUI. Das in-process-Backend (P9: torch/diffusers, SeedVR2, Flux-Panel) wird komplett
entfernt. Workflows werden per **Datei-Ablage** in `.photofant/workflows/` verfügbar gemacht
(Dateiname = interner Name, kein Upload/Aktivieren). Prompt, Auflösung und Maske werden
automatisch aus dem Workflow erkannt und über das bestehende Patch-System übergeben.

## Warum überhaupt

Das Patch-System steht bereits ([comfyui_run_job.py](../../../backend/photofant/jobs/comfyui_run_job.py)
`patch_template` setzt beliebige Werte auf beliebige Node-Felder). Es fehlen nur **Erkennung**
(Introspection sieht heute nur Bild-Loader), **UI** (Run-Leiste hat nur Bild-Slots) und ein
**einfacher Import** (heute Upload + Validieren + Aktivieren). P9 dupliziert Funktionalität,
die ComfyUI ohnehin liefert — koexistierende Doppelpflege ohne Mehrwert.

## Phasen-Übersicht

| # | Phase | Rating | Status |
|---|---|---|---|
| 1 | [Introspection erweitern](phase-1-introspection.md) — Prompt / Resolution / Alpha-Maske erkennen | heikel | complete |
| 2 | [FS-Discovery, DB raus](phase-2-fs-discovery.md) — Verzeichnis-Scan, Tabelle weg, Default-Zuordnung | heikel | complete |
| 3 | [P9 abreißen](phase-3-p9-abriss.md) — in-process generatives Backend entfernen | standard | complete |
| 4 | [Frontend: Settings + Service](phase-4-frontend-settings.md) — Auto-Liste, 3 Default-Dropdowns | standard | complete |
| 5 | [Frontend: Editor + Run-Leiste](phase-5-frontend-editor.md) — 3 Aufgaben + Bulk + generischer Trigger | heikel | pending |
| 6 | [Docs + ADR](phase-6-docs-adr.md) — ADR-008, code-map/routes/models/AGENTS | mechanisch | pending |

## Kontrakt (Backend ↔ Frontend)

In Phase 1/2 festgenagelt, danach stabil:

**Workflow-Discovery-DTO** (ein Eintrag pro `.json` im Verzeichnis):
```
key              # Dateiname ohne Endung — interner Name & Run-Selektor
name             # menschenlesbar (key, Underscores → Leerzeichen)
category         # erkannter Vorschlag: upscale | img2img | inpaint | generic
inputs[]         # Bild-Slots: { key, label, node_id, field, kind: image|mask }
prompt?          # { node_id, field } — positiver Prompt, falls erkannt
negative_prompt? # { node_id, field }
resolution?      # { node_id, megapixels_field, aspect_field, aspect_default } — falls ResolutionSelector
mask?            # { mode: 'alpha'|'loader', image_node_id } — falls Masken-Pfad erkannt
is_valid         # SaveImage vorhanden, API-Format, keine Binding-Drift
errors[]         # strukturierte Validierungsfehler (nur wenn invalid)
```

**Run-Request** (`POST /api/comfyui/workflows/{key}/run`):
```
inputs           # { slotKey → assetId | assetId[] }   (Batch = eine Listen-Achse)
face_inputs      # { slotKey → faceId | faceId[] }     (bestehend)
prompt?          # String → wird auf prompt.field gepatcht
negative_prompt? # String
resolution?      # { megapixels: float, aspect_ratio: string }
mask?            # { asset_id, mask_data_url } — Backend bettet Maske als Alpha ins Upload-PNG ein
```

**Defaults-API:** `GET/PUT /api/settings/comfyui` erweitert um
`default_upscale`, `default_edit`, `default_inpaint` (je ein Workflow-`key`).

## Finale Akzeptanzkriterien (Gesamtergebnis)

1. **Datei reinlegen genügt:** Eine `.json` in `Data/.photofant/workflows/` erscheint ohne
   weiteres Zutun in der Workflow-Liste; Bild-Slots, Prompt, Auflösung und Masken-Pfad sind
   automatisch erkannt. Kein Upload-Dialog, kein Aktivieren-Schritt.
2. **Default-Zuordnung:** In den Einstellungen ist je Aufgabe (Upscale / Image Edit / Inpaint)
   ein Workflow aus der Liste wählbar; die Wahl steht in `settings.json`.
3. **Editor:** Upscale (1-Klick, Default-Workflow), Image Edit (Prompt) und Inpaint
   (gemalte Maske + Prompt) laufen über ComfyUI. Galerie bietet Upscale als Bulk-Aktion.
4. **Generische Run-Leiste bleibt:** beliebiger Workflow mit frei gebundenen Bild-Slots,
   plus Prompt- und Auflösungs-Feldern, sofern der Workflow sie hat.
5. **Inpaint-Maske:** Die im Editor gemalte Maske landet im Alpha-Kanal des hochgeladenen
   PNGs; ein Flux-Fill-Workflow (LoadImage→`mask`-Slot) füllt nur den markierten Bereich.
6. **P9 ist weg:** kein torch/diffusers-Generativ-Stack, keine `api/generative.py`,
   keine upscale/flux_edit/inpaint/install_generative-Jobs, keine generativ-Rollen im Manifest.
7. `uv run ruff check .` grün · `npm run lint && npm run build` grün.

## Entschieden — schlanke Editor-Panels (2026-06-29)

**Das Editor-Mockup ist überholt.** [editor-tools.jsx](../../../docs/design/js/editor-tools.jsx)
zeichnet `UpscalePanel` (SeedVR2-Modellwahl, VRAM, fp8/GGUF, Ultimate-SD-Tiles) und `Flux2Panel`
(strength/steps/guidance/seed) — alles **P9-Parameter**, die voraussetzen, dass Photofant Modelle
und VRAM besitzt. Mit dem Abriss leben diese Werte im ComfyUI-Workflow, nicht in Photofant.

**Entscheidung (Sascha):** Panels radikal verschlanken. Sie zeigen nur, was der Workflow als
Parameter-Node exponiert (Prompt; Auflösung, falls ResolutionSelector). Modell-/Tile-/Step-Regler
entfallen ersatzlos. Das Mockup gilt für diese drei Panels als überholt — wird in Phase 6 in
`design-reconciliation.md` als bewusste Abweichung dokumentiert. Phase 5 setzt das um.

## Risiken & Annahmen

- 🟡 **Prompt-Erkennung ist Titel-Heuristik** (`CLIPTextEncode` mit „Positive"/„Negative" im
  `_meta.title`). Bricht bei umbenannten Titeln. Fallback: erster/einziger `CLIPTextEncode`
  = positiv. Workflows ohne erkennbaren Prompt bieten kein Prompt-Feld an.
- 🟡 **Inpaint-Maske = Alpha-Embedding**, nicht zweiter Slot. Erkennung über Node-Input
  `mask: [load_image_id, 1]`. Nur Workflows mit diesem Pfad unterstützen die gemalte Maske.
- 🟡 **`aspect_ratio`-Optionen** des ResolutionSelector sind ohne ComfyUI-`/object_info`-Abfrage
  nicht bekannt — wir übernehmen den Template-Default als einzige sichere Option und erlauben
  freie Megapixel-Eingabe. Volle Aspect-Liste optional über `/object_info` (Folge-Idee).
- 🟡 **`heavy_captioner`** (JoyCaption/Qwen-VL) teilt sich Manifest-Tier mit den Generativ-Rollen.
  Phase 3 darf **nur** die Bild-Generativ-Rollen (upscaler/editor/inpainter) entfernen, Captioner
  bleiben. Sweep klärt die Kopplung vor dem Löschen.

## Files touched
_(beim Archivieren füllen)_

## Commits
_(beim Archivieren füllen)_

## Deviations from plan
_(beim Archivieren füllen)_

## Follow-ups
_(beim Archivieren füllen)_
