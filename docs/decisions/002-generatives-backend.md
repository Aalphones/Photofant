# ADR-002 — Generatives Backend: diffusers (in-process)

**Status:** ~~Akzeptiert~~ **Ersetzt durch [ADR-008](008-generativ-via-comfyui.md)** · 2026-06-29
**Querverweise:** [ADR-003](003-comfyui-trigger-integration.md) (ComfyUI-Trigger, Fire-and-Forget, koexistierend) · [ADR-008](008-generativ-via-comfyui.md) (ersetzt diese Entscheidung)

---

## Kontext

Photofant braucht GPU-gebundene generative Features: Upscale (SeedVR2), Flux-Edit (img2img), Inpainting, und perspektivisch schwere Captioner (JoyCaption, Qwen-VL). Das Konzept (§3, §12) stellt zwei Kandidaten zur Wahl:

1. **diffusers (in-process):** torch + diffusers direkt im Backend-Prozess. Volle Kontrolle, kein externer Prozess, fp8/GGUF-Support über Bibliotheken.
2. **ComfyUI als Backend:** Eine lokale ComfyUI-Instanz als Inference-Server. Photofant steuert sie per REST-API, ComfyUI besitzt VRAM und Modelle.

ADR-003 hat parallel einen **dritten Weg** etabliert: ComfyUI als Fire-and-Forget-Trigger (P8b). Dieser Weg ist bereits implementiert und koexistiert unabhängig.

---

## Spike-Ergebnisse

### diffusers (in-process)

| Aspekt | Bewertung |
|---|---|
| fp8-safetensors | Nativ via `torchao`/`bitsandbytes`, auch über `diffusers`-Pipeline-Parameter (`torch_dtype`) |
| GGUF | Unterstützt via `gguf`-Package + `diffusers`-Integration (seit v0.30+) |
| VRAM-Kontrolle | Voll — load/unload on demand, `enable_model_cpu_offload()`, `enable_sequential_cpu_offload()` |
| Offline-Garantie | Trivial: `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` als Env-Vars beim Laden |
| Wartbarkeit | Eine Dependency-Gruppe, ein Prozess, kein IPC |
| Komponenten-Modelle | diffusers-Pipelines laden Teile separat (`unet`/`transformer`, `text_encoder`, `vae`) — passt zum Konzept §12.1 Komponenten-Picker |
| Install-Größe | ~2 GB (torch + CUDA wheels), einmalig |

### ComfyUI als Backend

| Aspekt | Bewertung |
|---|---|
| fp8/GGUF | Fertig via Custom Nodes (GGUF-Loader etc.) |
| VRAM-Kontrolle | ComfyUI managed — gut, aber keine Koordination mit Photofants ONNX-Sessions |
| Offline-Garantie | ComfyUI-seitig konfigurierbar, aber nicht von Photofant steuerbar |
| Wartbarkeit | Prozess-Management (Start/Stop/Health), REST-API-Kopplung, Workflow-Template-Pflege |
| Komponenten-Modelle | Workflow-basiert — flexibel, aber erfordert Workflow-Maintenance pro Feature |
| Install-Komplexität | User muss ComfyUI separat installieren + konfigurieren |

### Bewertung

diffusers gewinnt bei: Einfachheit (ein Prozess), VRAM-Koordination mit ONNX, Offline-Garantie, kein externes Setup. ComfyUI gewinnt bei: Workflow-Ökosystem (Custom Nodes), existierende Community-Workflows. Der Workflow-Vorteil wird bereits durch P8b (Fire-and-Forget-Trigger) abgedeckt — wer ComfyUI nutzen will, hat diesen Pfad.

---

## Entscheidung

**diffusers (in-process)** als generatives Backend für P9.

Begründung:
1. **Kein externer Prozess** — kein Start/Stop/Health-Management, kein IPC.
2. **VRAM-Koordination** — Photofant steuert ONNX-Sessions (Core) und torch-Modelle (Generativ) im selben Prozess. Ein generatives Modell zur Zeit, ONNX-Sessions werden bei Bedarf evicted.
3. **Offline-Garantie trivial** — Env-Vars setzen, fertig.
4. **P8b deckt den ComfyUI-Use-Case** — wer ComfyUI-Workflows nutzen will, hat den Fire-and-Forget-Pfad.
5. **Komponenten-Modelle passen** — diffusers lädt Transformer, Text-Encoder und VAE aus separaten Pfaden.

---

## Architektur

```
Inference-Layer
├── session_manager.py       (ONNX, besteht)
├── generative_engine.py     (torch/diffusers, NEU)
└── interfaces.py            (Protocols: bestehende + Upscaler/Editor/Inpainter)
```

- **GenerativeEngine** — Singleton, analog zum ONNX SessionManager. Lädt eine diffusers-Pipeline zur Zeit, evictet idle Pipelines. Setzt Offline-Env-Vars vor dem Laden.
- **Ein Modell zur Zeit** — VRAM-Constraint. Wechsel: altes Modell entladen, VRAM freigeben, neues laden.
- **Komponenten-Support** — Pipeline wird aus separaten Pfaden zusammengebaut (`model_registry.components`-Map).
- **Optional gated** — torch/diffusers sind eine optionale Dependency-Gruppe. Ohne Installation sind alle generativen Features disabled mit Hinweis.

---

## Konsequenzen

- torch/diffusers als `[project.optional-dependencies] generative` — Installation über die UI angestoßen.
- `GenerativeEngine` muss ONNX-SessionManager bei VRAM-Knappheit koordinieren (ONNX-Sessions evicten, bevor ein großes torch-Modell geladen wird).
- fp8-Support über `torchao` oder `bitsandbytes`, GGUF über `gguf`-Package — beides in der generative-Dependency-Gruppe.
- Manifest erweitert um Rollen `upscaler`, `editor`, `heavy_captioner`; `generativ`-Tier.
- Validierungs-Pipeline (§12.2a) muss um safetensors/GGUF-Format-Erkennung erweitert werden — erkennt sie bereits (magic bytes), braucht nur neue Rollen-Zuordnung.

---

> **Hinweis (P16, 2026-06-29):** Diese Entscheidung wurde durch [ADR-008](008-generativ-via-comfyui.md)
> ersetzt. Das diffusers in-process Backend (SeedVR2, Flux-Edit, Inpaint) wurde vollständig entfernt.
> Upscale/Edit/Inpaint laufen ausschließlich über ComfyUI. Die `heavy_captioner`-Rolle (JoyCaption,
> Qwen-VL) und die torch/transformers-Infrastruktur in `generative_engine.py` bleiben bestehen.
