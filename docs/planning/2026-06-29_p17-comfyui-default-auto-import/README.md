# P17 - ComfyUI Default-Workflows importieren Ergebnisse automatisch

**Status:** In Umsetzung
**ADR:** [009](../../decisions/009-comfyui-default-auto-import.md)

## Ziel

Upscale, Image Edit und Inpaint laufen weiter ueber ComfyUI, aber die drei in den Einstellungen
gesetzten Default-Workflows schreiben ihr Ergebnis automatisch als neue Edit-Version am Quellbild
zurueck. Die generische Run-Leiste bleibt bewusst Fire-and-forget: Ergebnisliste und manueller
Import bleiben dort der richtige Ablauf.

## Chesterton's Fence

Der bestehende ComfyUI-Run ist Fire-and-forget, weil ADR-003 Photofant nur als Trigger fuer beliebige
Workflows definiert hat: Bild hochladen, Workflow patchen, Prompt absenden, Ergebnis in ComfyUIs
`output/` lassen. Das schuetzt generische Experimente vor unerwarteten DB-Aenderungen. Verstanden:
Diese Regel bleibt fuer die Run-Leiste bestehen. P17 fuehrt Auto-Import nur fuer die drei kuratierten
Default-Aktionen ein, weil dort die Nutzererwartung anders ist: "Upscale/Edit/Inpaint anwenden"
bedeutet ein neues Bild in Photofant, nicht eine lose Datei in ComfyUIs Output-Ordner.

## Kontrakt

Neuer Default-Run-Endpunkt:

```text
POST /api/comfyui/defaults/{task}/run
task = upscale | edit | inpaint

Request:
  target_asset_ids: int[]
  inputs: { slotKey -> assetId | assetId[] }
  face_inputs?: { slotKey -> faceId | faceId[] }
  prompt?: string
  negative_prompt?: string
  resolution?: { megapixels: float, aspect_ratio: string }
  mask?: { asset_id: int, mask_data_url: string }

Response:
  { jobs: [{ job_id }] }
```

Regeln:

- Der Endpunkt nimmt den Workflow-Key nur aus `settings.json` (`default_upscale`, `default_edit`,
  `default_inpaint`). Kein freier Workflow-Key, kein Auto-Import fuer die Run-Leiste.
- Jeder expandierte Job bekommt genau einen `target_asset_id`. Bei Bulk muss die Anzahl zu den
  expandierten Jobs passen.
- Der bestehende Endpunkt `POST /api/comfyui/workflows/{key}/run` bleibt Fire-and-forget.
- Auto-Import akzeptiert nur Workflows mit eindeutigem Bild-Output: bevorzugt ein Save-Node mit
  `_meta.title = "Photofant Output"`, sonst genau ein SaveImage-kompatibler Output. Mehrdeutige
  Outputs blockieren den Default-Run mit klarer Fehlermeldung.
- Importierte Versionen bekommen `type = "comfyui"` und `params.source = "comfyui_auto_import"` plus
  `task`, `workflow_key`, `prompt_id`, `source_filename`, `source_subfolder`, `width`, `height`.
- Nach erfolgreichem Import wird die importierte ComfyUI-Output-Datei geloescht, sofern sie lokal
  ueber den konfigurierten `comfyui.output_dir` sicher aufloesbar ist. Remote-only Abruf ueber
  `/view` kann nicht aufraeumen und wird als sauberer Skip geloggt.

## Settings-Keys

Diese tunablen Werte sind fuer Phase 2 bestaetigt und gehoeren gemaess Projektregel in
`settings.json`, nicht als Modul-Konstanten:

```text
comfyui.result_poll_interval_seconds = 1.0
comfyui.result_wait_timeout_seconds = 1800
```

## Phasen

| Phase | Inhalt | Rating | Status |
|---|---|---:|---|
| 1 | [Kontrakt + ADR](phase-1-contract-adr.md) | heikel | complete |
| 2 | [Backend: Warten, Ergebnis finden, importieren](phase-2-backend-auto-import.md) | heikel | pending |
| 3 | [Frontend: Default-Flows umhaengen](phase-3-frontend-default-flows.md) | standard | pending |

## Finale Akzeptanzkriterien

1. Upscale, Image Edit und Inpaint aus Editor/Galerie legen nach erfolgreichem ComfyUI-Lauf automatisch
   eine aktuelle Edit-Version am jeweiligen Asset an.
2. Bulk-Upscale legt pro Quellbild genau eine neue Version am passenden Asset an.
3. Die generische Run-Leiste nutzt weiterhin ausschliesslich `POST /api/comfyui/workflows/{key}/run`
   und importiert nichts automatisch.
4. Mehrdeutige oder output-lose Default-Workflows scheitern vor dem Submit mit verstaendlicher Meldung.
5. Job-Status zeigt Warten auf ComfyUI und Import als Teil desselben Jobs; die UI blockiert nicht.
6. Erfolgreich automatisch importierte lokale ComfyUI-Output-Dateien werden geloescht; generische
   Fire-and-forget-Outputs bleiben unberuehrt.
7. Manuelle Ergebnisliste und manueller Import bleiben fuer generische Workflows erhalten.
8. Backend-Lint und Frontend-Lint/Build sind gruen.

## Risiken

- Mehrere SaveImage-Nodes sind in ComfyUI-Workflows normal. Ohne Output-Regel wuerden wir zufaellig
  importieren. Das waere Daten-Schlamm mit UI-Krawatte.
- ComfyUI-History kann kurz leer sein, obwohl der Prompt noch laeuft. Der Job braucht Polling mit
  Timeout und klare Fehler, nicht "fertig" direkt nach Submit.
- Batch-Zuordnung darf nicht aus Dateinamen geraten werden. `target_asset_ids` ist absichtlich
  explizit.
- Cleanup ist potentiell destruktiv. Geloescht wird deshalb nur nach erfolgreichem DB-Commit und nur
  ein Pfad, der per Resolve-Pruefung unter `comfyui.output_dir` liegt. Alles andere bleibt liegen.

## Summary

Noch offen.

## Files touched

Noch offen.

## Commits

Noch offen.

## Deviations from plan

Noch offen.

## Follow-ups

Noch offen.
