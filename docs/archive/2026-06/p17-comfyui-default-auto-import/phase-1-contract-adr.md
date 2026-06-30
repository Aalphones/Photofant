# Phase 1 - Kontrakt + ADR

**Status:** complete

**Rating:** heikel

## Kontext

- [docs/decisions/003-comfyui-trigger-integration.md](../../../docs/decisions/003-comfyui-trigger-integration.md)
- [docs/decisions/008-generativ-via-comfyui.md](../../../docs/decisions/008-generativ-via-comfyui.md)
- [docs/routes.md](../../../docs/routes.md) - ComfyUI-Routen
- [docs/code-map.md](../../../docs/code-map.md) - Generativ / ComfyUI-Zeilen
- [backend/photofant/api/comfyui.py](../../../backend/photofant/api/comfyui.py)
- [backend/photofant/jobs/comfyui_run_job.py](../../../backend/photofant/jobs/comfyui_run_job.py)
- [backend/photofant/comfyui/introspect.py](../../../backend/photofant/comfyui/introspect.py)
- [backend/photofant/comfyui/validator.py](../../../backend/photofant/comfyui/validator.py)

## Akzeptanzkriterien

1. ADR-009 angelegt: Default-Workflows importieren automatisch, generische Run-Leiste bleibt
   Fire-and-forget.
2. ADR-003 und ADR-008 bekommen kurze Querverweise auf ADR-009, ohne die alte Historie glattzubuegeln.
3. Der README-Kontrakt bleibt die Quelle fuer Route, Request, Response, Output-Auswahl und Settings-Keys.
4. Entscheidung zur Output-Auswahl dokumentiert:
   - bevorzugt Save-Node mit `_meta.title = "Photofant Output"`
   - sonst genau ein SaveImage-kompatibler Output
   - mehrere unmarkierte Outputs sind fuer Defaults invalid
5. Entscheidung zu Settings-Keys bestaetigt oder im Plan angepasst, bevor Phase 2 startet.

## Checkliste

- [x] `docs/decisions/009-comfyui-default-auto-import.md` anlegen
- [x] ADR-003/-008 um Querverweis ergaenzen
- [x] `docs/routes.md` geplante neue Default-Run-Route nachziehen
- [x] `docs/code-map.md` Generativ/ComfyUI-Zeile um Auto-Import-Pfad ergaenzen
- [x] Settings-Keys finalisieren

## Report-Back

ADR-009 ist angelegt. Der Vertrag fuer den Default-Run steht in README und
`docs/routes.md`; die Output-Auswahl ist auf `Photofant Output`-Marker oder genau
einen unmarkierten SaveImage-kompatiblen Output festgelegt. Settings-Keys fuer Polling
und Timeout sind fuer Phase 2 bestaetigt.
