# ADR-008 — Generativ via ComfyUI (P9 entfernt)

**Status:** Akzeptiert · 2026-06-29
**Querverweise:**
- [ADR-002](002-generatives-backend.md) — **ersetzt** (diffusers in-process → nicht mehr verwendet)
- [ADR-003](003-comfyui-trigger-integration.md) — **erweitert** (Fire-and-Forget wird jetzt auch für Upscale/Edit/Inpaint genutzt)
- [ADR-009](009-comfyui-default-auto-import.md) — **praezisiert** (Default-Workflows importieren Ergebnisse automatisch)

---

## Kontext

ADR-002 entschied sich für diffusers in-process (P9) als generatives Backend. P16 kehrt
diese Entscheidung um: Das in-process-Backend (torch/diffusers, SeedVR2, Flux-Panels) wird
vollständig entfernt. Upscale, Image Edit und Inpaint laufen ausschließlich über ComfyUI —
denselben Mechanismus, den ADR-003 (P8b) für den Fire-and-Forget-Pfad etabliert hat.

**Auslöser:** ADR-002 begründete diffusers hauptsächlich mit VRAM-Koordination und
Offline-Garantie. In der Praxis stellte sich heraus: Das Patch-System (Kontrakt-Werte in
beliebige Workflow-Knoten injizieren) war bereits in `comfyui_run_job.py` vorhanden, und
ComfyUI-Workflows bringen Modellwahl, Tile-Strategie und Sampling-Parameter von Haus aus
mit — Photofant muss das nicht doppelt pflegen.

---

## Optionen

| Option | Beschreibung |
|---|---|
| **A — P9 entfernen, ComfyUI übernimmt alles** | Drei generative Aufgaben laufen über ComfyUI-Workflows; Modell-/VRAM-Kontrolle liegt bei ComfyUI. |
| B — P9 und ComfyUI koexistieren (Status quo) | Doppelpflege zweier Generativ-Stacks ohne konkreten Mehrwert für den typischen Nutzer. |
| C — P9 ausbauen, ComfyUI entfernen | Würde den Fire-and-Forget-Pfad opfern; schlechtere UX für Nutzer mit vorhandener ComfyUI-Installation. |

---

## Entscheidung

**Option A.** Das in-process generative Backend (P9) wird entfernt.

Begründung:

1. **Keine Doppelpflege.** SeedVR2, Flux-Pipelines und GGUF-Loader werden in ComfyUI-Workflows
   von der Community gepflegt. Photofant muss nur das Patch-System kennen, nicht die Modell-Interna.
2. **Workflow-Discovery statt Upload.** Eine `.json`-Datei in `.photofant/workflows/` erscheint
   automatisch in der Liste — kein Upload-Dialog, kein Aktivieren-Schritt.
3. **Schlankere Panels.** Der Editor zeigt nur, was der Workflow als Parameter exponiert (Prompt,
   Auflösung, Maske). Modell-/Step-Regler liegen im Workflow, nicht in der UI.
4. **torch/transformers bleiben.** Der Heavy-Captioner-Stack (JoyCaption, Qwen-VL) teilt sich
   `generative_engine.py`-Infrastruktur (load/evict). Nur die diffusers-Methoden werden entfernt.
5. **Offline-Garantie bleibt erhalten.** ComfyUI wird lokal betrieben; kein externer Netzwerkverkehr.

---

## Architektur nach P16

```
Generativ (Upscale / Edit / Inpaint)
    → api/comfyui.py  POST /api/comfyui/workflows/{key}/run
    → jobs/comfyui_run_job.py  (Patch + Queue + Fire)
    → ComfyUI-Instanz  (VRAM- + Modell-Owner)

Ergebnis-Import (bewusster Schritt)
    → POST /api/comfyui/results/import  (type = "comfyui")

Default-Import (kuratiert, nicht generisch)
    → POST /api/comfyui/defaults/{task}/run
    → wartet auf ComfyUI-History und importiert genau ein definiertes Ergebnis

Workflow-Discovery (Dateisystem)
    → .photofant/workflows/*.json  (kein DB-Eintrag)
    → comfyui/introspect.py  (Prompt / Resolution / Mask erkennen)
    → comfyui/validator.py   (SaveImage, API-Format, Binding-Drift)

Heavy Captioners (bleiben in-process)
    → inference/generative_engine.py  (load_transformers_model, evict)
    → inference/adapters/joycaption.py, qwen_vl.py
```

**Entfernt (P9):**

- `inference/` — diffusers-Methoden aus `generative_engine.py`; `interfaces.py` Upscaler/Editor/Inpainter-Protocols
- `api/generative.py` — `/generative/status`, `/install`, `/unload`
- `api/assets.py` — upscale/bulk-upscale/flux-edit/inpaint-Endpoints + DTOs
- `jobs/` — `upscale_job.py`, `flux_edit_job.py`, `inpaint_job.py`, `install_generative_job.py`
- `models/manifest.json` — flux2-klein-9b, seedvr2-3b, seedvr2-7b
- `models/loader.py` — Rollen `upscaler`, `editor`, `inpainter`
- `pyproject.toml` — `diffusers>=0.31` aus der `generative`-Gruppe

---

## Kontrakt (Frontend ↔ Backend)

**Workflow-Discovery-DTO** (ein Eintrag pro `.json` im Verzeichnis):

```
key              # Dateiname ohne Endung — interner Name & Run-Selektor
name             # menschenlesbar (key, Underscores → Leerzeichen)
category         # erkannter Vorschlag: upscale | img2img | inpaint | generic
inputs[]         # Bild-Slots: { key, label, node_id, field, kind: image|mask }
prompt?          # { node_id, field } — positiver Prompt (Titel-Heuristik: "Positive")
negative_prompt? # { node_id, field }
resolution?      # { node_id, megapixels_field, aspect_field, aspect_default }
mask?            # { mode: 'alpha'|'loader', image_node_id }
is_valid         # SaveImage vorhanden, API-Format, keine Binding-Drift
errors[]         # strukturierte Validierungsfehler
```

**Run-Request** (`POST /api/comfyui/workflows/{key}/run`):

```
inputs           # { slotKey → assetId | assetId[] }
face_inputs      # { slotKey → faceId | faceId[] }
prompt?          # String → wird auf prompt.field gepatcht
negative_prompt? # String
resolution?      # { megapixels: float, aspect_ratio: string }
mask?            # { asset_id, mask_data_url } — Alpha-Embedding via Upload-PNG
```

**Prompt-Erkennung:** Nur über `_meta.title`-Match (`Positive`/`Negative` im Knoten-Titel).
Der „Single-CLIPTextEncode-Fallback" wurde bewusst weggelassen — er kollidiert mit
SeedVR2-Workflows, wo das einzige `CLIPTextEncode` ein interner Upscaler-Prompt ist.
Workflows ohne explizit benannte Nodes bieten kein Prompt-Feld an.

---

## Konsequenzen

- ComfyUI-Installation ist Voraussetzung für alle drei generativen Aufgaben (kein lokaler Fallback mehr).
- `generative`-Dependency-Gruppe in `pyproject.toml` bleibt bestehen, enthält aber nur noch torch/transformers/accelerate (Heavy Captioners), nicht mehr diffusers.
- `CapabilitiesDto` enthält keine `upscale`/`flux_edit`/`inpaint`-Felder mehr; Gating läuft über `comfyui.enabled`.
- Editor-Panels zeigen nur Workflow-Parameter (Prompt, Auflösung) — keine Modell-/Step-Regler.
- Inpaint-Maske wird als Alpha-Kanal in ein Upload-PNG eingebettet; Workflows mit `mask: [load_image_id, 1]`-Pfad unterstützen die gemalte Maske.
- Auto-Import gilt nur fuer die drei Default-Aufgaben aus den Einstellungen. Der freie Workflow-Run bleibt Fire-and-forget.
