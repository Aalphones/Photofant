# Phase 1 — Introspection erweitern

**Rating:** heikel (neue Erkennungs-Heuristik, formt den Kontrakt)

## Kontext (lesen)

- [backend/photofant/comfyui/introspect.py](../../../backend/photofant/comfyui/introspect.py) — heutige Erkennung (nur Bild-Loader)
- [backend/photofant/comfyui/validator.py](../../../backend/photofant/comfyui/validator.py) — Binding-Validierung
- [backend/photofant/jobs/comfyui_run_job.py](../../../backend/photofant/jobs/comfyui_run_job.py) — `patch_template` (Ziel der Bindings)
- Die vier Beispiel-Workflows im Projekt-Root (`Flux Edit.json`, `Clean Studio Photo.json`, `SeedVR2.json`, `Inpaint.json`) — Referenz für die Heuristik. **Sind untracked und werden nach P16 abgeräumt** → in dieser Phase als Test-Fixtures nach `backend/tests/fixtures/comfyui/` (normalisierte Namen) übernehmen, bevor sie verschwinden.
- [docs/conventions/python.md](../../../docs/conventions/python.md)

## Akzeptanzkriterien

1. **Prompt-Erkennung:** `introspect_template` liefert für `CLIPTextEncode`-Nodes ein
   `prompt` / `negative_prompt`-Ergebnis (`node_id`, `field='text'`). Zuordnung über `_meta.title`
   (enthält „Positive"/„Negative", case-insensitiv). Fallback: genau ein `CLIPTextEncode` → positiv.
2. **Resolution-Erkennung:** Ein `ResolutionSelector`-Node liefert `resolution`
   (`node_id`, `megapixels_field='megapixels'`, `aspect_field='aspect_ratio'`,
   `aspect_default` = Template-Wert). Kein Selector → kein `resolution`.
3. **Masken-Erkennung (Alpha-Pfad):** Findet einen Node mit Input `mask: [X, 1]`, wobei `X` ein
   `LoadImage` ist → `mask = { mode:'alpha', image_node_id: X }`. Der klassische `LoadImageMask`
   bleibt als `mode:'loader'` erkannt (bisheriges Verhalten, `kind=mask`).
4. **Kategorie-Vorschlag:** `category` wird heuristisch gesetzt — Upscale-Nodes
   (`SeedVR2VideoUpscaler`, `UltimateSDUpscale`, `ImageUpscaleWithModel`, `UpscaleModelLoader`)
   → `upscale`; Masken-Pfad / `InpaintModelConditioning` → `inpaint`; Edit/`ReferenceLatent`
   ohne Maske → `img2img`; sonst `generic`. (Vorschlag, nicht bindend — User wählt Defaults.)
5. **Vier Beispiel-Workflows korrekt erkannt** (prüfbar per Test):
   - `Flux Edit.json`: Bild-Input „Input Image", positiv+negativ Prompt, **keine** Resolution, keine Maske → `img2img`.
   - `Clean Studio Photo.json`: Bild-Input, positiv+negativ Prompt, Resolution (megapixels=2, aspect="2:3 (Portrait Photo)") → `img2img`.
   - `SeedVR2.json`: Bild-Input, kein Prompt-Feld für User, keine Resolution → `upscale`.
   - `Inpaint.json`: Bild-Input „Load Image", positiv Prompt, Maske `mode='alpha', image_node_id='17'` → `inpaint`.
6. Bestehende Bild-Slot-Erkennung unverändert (Regressionsschutz).

## Checkliste

- [x] `introspect.py`: Datenklassen um `PromptInfo`, `ResolutionInfo`, `MaskInfo` erweitern; `IntrospectionResult` um `prompt`, `negative_prompt`, `resolution`, `mask`, `category` ergänzen
- [x] Prompt-Heuristik (Titel-Match; Single-Encode-Fallback bewusst weggelassen — siehe Report-Back)
- [x] Resolution-Heuristik (`ResolutionSelector` → Felder + Default)
- [x] Masken-Heuristik (Alpha-Pfad über `mask: [id,1]` + Loader-Pfad)
- [x] Kategorie-Heuristik (Node-Klassen-Signaturen)
- [~] Unit-Test gegen die vier Beispiel-Workflows (AK 5) — entfällt, private-Profil: keine Tests; Heuristik manuell an den vier Workflows verifiziert (lokal ausgeführt, nicht committed)
- [x] `validator.py`: Prompt/Resolution/Mask-Bindings mitvalidieren (Feld existiert im Zielnode) → `validate_introspection_result()`
- [x] Doc-Update: Kontrakt-DTO in README bestätigt — `PromptInfo`/`ResolutionInfo`/`MaskInfo` matchen exakt, kein Anpassungsbedarf

## Report-Back

**Umsetzung:** `introspect.py` + `validator.py` erweitert. Neue Typen: `WorkflowCategory` (StrEnum), `PromptInfo`, `ResolutionInfo`, `MaskInfo`. `IntrospectionResult` um `prompt`, `negative_prompt`, `resolution`, `mask`, `category` ergänzt. Keine Tests (private-Profil — keine Backend-Tests außer Move-Tests). Heuristik lokal gegen alle vier Beispiel-Workflows geprüft, alle AK5-Fälle korrekt erkannt.

**Abweichung von AK1:** Der „Single-Encode-Fallback" (genau ein CLIPTextEncode → positiv) wurde **nicht** implementiert. AK5 verlangt für SeedVR2 (hat genau einen, Titel „CLIP Text Encode (Prompt)") kein Prompt-Feld — das widerspricht dem Fallback. Entscheidung: nur explizite Titel-Matches (Positive/Negative) erzeugen Prompt-Felder. Interne Upscaler-Prompts ohne Positive/Negative-Kennzeichnung werden absichtlich nicht exponiert. → FINDINGS für Phase 6 (Doku).
