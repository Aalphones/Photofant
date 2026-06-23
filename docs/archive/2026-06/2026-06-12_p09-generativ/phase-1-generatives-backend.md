# P9 · Phase 1 — Generatives Backend (ADR)

> Rating: **heikel** (Architektur-Entscheidung mit Folgekosten für alle generativen Phasen) · Status: **complete**

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Offline-Garantie, Dependency-Gruppe)
- [Konzept](../../Konzept-Photofant.md) §3 (torch+diffusers **oder** ComfyUI-Backend), §12.2 (fp8/GGUF-Pflicht), §19.4

## Akzeptanzkriterien

- **ADR-002** (`docs/decisions/002-generatives-backend.md`): diffusers (in-process, volle Kontrolle, fp8/GGUF-Support selbst lösen) vs. ComfyUI als lokales Backend (Workflow-Ökosystem, GGUF-Nodes fertig, aber Prozess-Management + API-Kopplung). Spike: je ein img2img-Durchstich. Kriterien: GGUF/fp8-Ladbarkeit, VRAM-Verhalten, Wartbarkeit, Offline-Sauberkeit.
- torch/diffusers (bzw. ComfyUI-Anbindung) als optionale uv-Dependency-Gruppe; Installation per UI-Aktion mit Job + verständlicher Erklärung (Download-Größe!).
- `GenerativeEngine`-Interface im Inferenz-Layer (Upscaler/Editor/Inpainter-Protocols), Offline-Env-Variablen beim Laden gesetzt.

## Checkliste

- [x] Spike beider Kandidaten (Wegwerf-Branch/Notizen in FINDINGS)
- [x] ADR-002 schreiben (Empfehlung + Trade-offs)
- [x] Dependency-Gruppe + Install-Job + UI-Hinweisfluss
- [x] Engine-Interfaces + Lade-/Entlade-Strategie (VRAM ist knapp: ein generatives Modell zur Zeit)
- [x] Doc-Update: docs/decisions/002, AGENTS.md Stack-Tabelle

## Report-Back

**Ergebnis:** diffusers (in-process) als generatives Backend gewählt (ADR-002).

**Geliefert:**
- `docs/decisions/002-generatives-backend.md` — ADR mit Spike-Analyse
- `backend/photofant/inference/generative_engine.py` — Singleton-Engine, ein Modell zur Zeit, idle-eviction, Offline-Env-Vars, Komponenten-Support
- `backend/photofant/inference/interfaces.py` — Protocols: `Upscaler`, `ImageEditor`, `Inpainter`
- `backend/pyproject.toml` — generative Dependency-Gruppe erweitert (torch, diffusers, transformers, accelerate, safetensors, sentencepiece)
- `backend/photofant/jobs/install_generative_job.py` — Install-Job (uv pip install, Queue-basiert)
- `backend/photofant/api/generative.py` — `/api/generative/status`, `/install`, `/unload`
- `backend/photofant/models/manifest.json` — FLUX.2 klein 9B (editor), SeedVR2 3B/7B (upscaler) mit Varianten-Matrix
- `backend/photofant/models/loader.py` — Rollen `upscaler`, `editor`, `heavy_captioner` akzeptiert
- AGENTS.md Stack-Tabelle aktualisiert
