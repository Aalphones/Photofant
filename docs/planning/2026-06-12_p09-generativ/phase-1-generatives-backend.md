# P9 · Phase 1 — Generatives Backend (ADR)

> Rating: **heikel** (Architektur-Entscheidung mit Folgekosten für alle generativen Phasen) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Offline-Garantie, Dependency-Gruppe)
- [Konzept](../../Konzept-Photofant.md) §3 (torch+diffusers **oder** ComfyUI-Backend), §12.2 (fp8/GGUF-Pflicht), §19.4

## Akzeptanzkriterien

- **ADR-002** (`docs/decisions/002-generatives-backend.md`): diffusers (in-process, volle Kontrolle, fp8/GGUF-Support selbst lösen) vs. ComfyUI als lokales Backend (Workflow-Ökosystem, GGUF-Nodes fertig, aber Prozess-Management + API-Kopplung). Spike: je ein img2img-Durchstich. Kriterien: GGUF/fp8-Ladbarkeit, VRAM-Verhalten, Wartbarkeit, Offline-Sauberkeit.
- torch/diffusers (bzw. ComfyUI-Anbindung) als optionale uv-Dependency-Gruppe; Installation per UI-Aktion mit Job + verständlicher Erklärung (Download-Größe!).
- `GenerativeEngine`-Interface im Inferenz-Layer (Upscaler/Editor/Inpainter-Protocols), Offline-Env-Variablen beim Laden gesetzt.

## Checkliste

- [ ] Spike beider Kandidaten (Wegwerf-Branch/Notizen in FINDINGS)
- [ ] ADR-002 schreiben (Empfehlung + Trade-offs)
- [ ] Dependency-Gruppe + Install-Job + UI-Hinweisfluss
- [ ] Engine-Interfaces + Lade-/Entlade-Strategie (VRAM ist knapp: ein generatives Modell zur Zeit)
- [ ] Doc-Update: docs/decisions/002, AGENTS.md Stack-Tabelle

## Report-Back
