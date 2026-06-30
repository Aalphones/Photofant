# ADR-009 - ComfyUI Default-Workflows mit Auto-Import

**Status:** Akzeptiert - 2026-06-30
**Querverweise:**
- [ADR-003](003-comfyui-trigger-integration.md) - bleibt fuer generische Workflows Fire-and-forget
- [ADR-008](008-generativ-via-comfyui.md) - ComfyUI bleibt einziger Generativ-Pfad

---

## Kontext

ADR-003 hat Photofant bewusst als ComfyUI-Trigger definiert: Workflow patchen,
Prompt absenden, Ergebnis in ComfyUIs `output/` lassen. Das ist fuer die generische
Run-Leiste richtig, weil beliebige Experimente keine stillen DB-Aenderungen ausloesen
duerfen.

Seit ADR-008 laufen aber auch Upscale, Image Edit und Inpaint ueber ComfyUI. Diese drei
Aktionen sind keine freien Experimente, sondern kuratierte Default-Flows aus den
Einstellungen. Dort erwartet der Nutzer nach "anwenden" ein neues Bild in Photofant,
nicht eine lose Datei in ComfyUIs Ausgabeordner.

---

## Entscheidung

Photofant bekommt einen eigenen Default-Run-Endpunkt fuer die drei kuratierten Aufgaben:

```text
POST /api/comfyui/defaults/{task}/run
task = upscale | edit | inpaint
```

Der Endpunkt liest den Workflow-Key ausschliesslich aus `settings.json`:

- `default_upscale` fuer `upscale`
- `default_edit` fuer `edit`
- `default_inpaint` fuer `inpaint`

Der bestehende Endpunkt `POST /api/comfyui/workflows/{key}/run` bleibt unveraendert
Fire-and-forget. Er importiert keine Ergebnisse automatisch und loescht keine Dateien.

---

## Vertrag

Request:

```text
target_asset_ids: int[]
inputs: { slotKey -> assetId | assetId[] }
face_inputs?: { slotKey -> faceId | faceId[] }
prompt?: string
negative_prompt?: string
resolution?: { megapixels: float, aspect_ratio: string }
mask?: { asset_id: int, mask_data_url: string }
```

Response:

```text
{ jobs: [{ job_id }] }
```

Regeln:

- Jeder expandierte Job bekommt genau einen `target_asset_id`.
- Bei Bulk muss die Anzahl der expandierten Jobs exakt zu `target_asset_ids` passen.
- Kein freier Workflow-Key auf dem Default-Endpunkt.
- Kein Auto-Import fuer die generische Run-Leiste.
- Der Job wartet nach `POST /prompt` auf ComfyUIs History-Eintrag und importiert danach
  genau das definierte Ergebnis als neue Edit-Version am Ziel-Asset.
- Importierte Versionen bekommen `type = "comfyui"` und
  `params.source = "comfyui_auto_import"`.
- Die Params enthalten mindestens `task`, `workflow_key`, `prompt_id`,
  `source_filename`, `source_subfolder`, `width` und `height`.

---

## Output-Auswahl

Default-Workflows sind nur gueltig, wenn genau ein importierbares Bild eindeutig
bestimmt werden kann:

1. Bevorzugt wird ein Save-Node mit `_meta.title = "Photofant Output"`.
2. Ohne Marker ist genau ein SaveImage-kompatibler Output erlaubt.
3. Mehrere unmarkierte SaveImage-kompatible Outputs machen den Default-Workflow invalid.
4. Workflows ohne SaveImage-kompatiblen Output sind fuer Defaults invalid.

SaveImage-kompatibel meint die bereits unterstuetzten Output-Klassen aus der
ComfyUI-Introspection, die ein Bild in History oder `output/` liefern.

---

## Warten, Timeout, Cleanup

Der Default-Job pollt ComfyUIs History bis zum Ergebnis oder Timeout:

```text
comfyui.result_poll_interval_seconds = 1.0
comfyui.result_wait_timeout_seconds = 1800
```

Diese Werte sind Settings-Keys, keine Modul-Konstanten. Sie duerfen in der
Settings-Datei fehlen; dann gelten die oben genannten Defaults.

Nach erfolgreichem DB-Commit loescht Photofant die importierte lokale Output-Datei,
wenn sie sicher unter dem konfigurierten `comfyui.output_dir` aufgeloest werden kann.
Remote-only Abruf ueber ComfyUI `/view` kann nicht lokal aufraeumen und wird nur geloggt.

---

## Konsequenzen

- Die generische Run-Leiste bleibt ein sauberer Trigger fuer beliebige Workflows.
- Upscale, Edit und Inpaint erhalten die erwartete "neue Version am Bild"-Semantik.
- Mehrdeutige Default-Workflows scheitern vor dem Submit mit klarer Fehlermeldung.
- Output-Cleanup bleibt eng begrenzt: nur nach erfolgreichem Import, nur lokal, nur unter
  `comfyui.output_dir`.
