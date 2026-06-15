# P5 · Phase 1 — Inferenz-Layer

> Rating: **heikel** (Architektur-Phase: Interfaces, Session-Lifecycle, CPU/GPU) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — interner Kontrakt (Protocol-Interfaces)
- [Konzept](../../Konzept-Photofant.md) §2 (Inferenz-Layer), §12.5 (Tiers)
- P4-Registry (Modell-Pfade/Status kommen von dort)

## Akzeptanzkriterien

- `photofant/inference/`: Protocol-Interfaces pro Rolle + Engine-Verwaltung — ONNX-Sessions lazy laden, nach Idle-Timeout entladen (RAM/VRAM), Provider-Wahl CPU/CUDA/DirectML automatisch mit Override in `app_config`.
- Modell-Auflösung läuft ausschließlich über die P4-Registry (`enabled` + `is_default`); kein hartkodierter Pfad.
- Inferenz läuft in einem Thread-Executor (onnxruntime ist blocking) — die async Queue bleibt responsiv.
- Fehlerverhalten: Modell lädt nicht → Job-Error mit Fehlercode, Feature-Status bleibt korrekt; nie ein halb geladenes Modell im Cache.

## Checkliste

- [ ] Interfaces (`Tagger`, `Captioner`, `Embedder`, später `FaceEngine` in P7) + Registry-Auflösung
- [ ] Session-Manager (lazy load, idle unload, Provider-Detection inkl. Logging der gewählten Provider)
- [ ] Executor-Anbindung an die Job-Queue (CPU-bound-Schutz)
- [ ] Preprocessing-Utilities (Resize/Normalize je Modell-Familie, ein Ort)
- [ ] Doc-Update: docs/decisions/ — kurzes ADR nur falls Provider-Strategie nicht-offensichtlich ausfällt

## Report-Back
