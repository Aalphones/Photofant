# P5 · Phase 1 — Inferenz-Layer

> Rating: **heikel** (Architektur-Phase: Interfaces, Session-Lifecycle, CPU/GPU) · Status: complete

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

- [x] Interfaces (`Tagger`, `Captioner`, `Embedder`, später `FaceEngine` in P7) + Registry-Auflösung
- [x] Session-Manager (lazy load, idle unload, Provider-Detection inkl. Logging der gewählten Provider)
- [x] Executor-Anbindung an die Job-Queue (CPU-bound-Schutz) — `session_manager.executor` (ThreadPoolExecutor, 1 Worker)
- [x] Preprocessing-Utilities (Resize/Normalize je Modell-Familie, ein Ort)
- [x] Doc-Update: Provider-Strategie ist offensichtlich (DML→CUDA→CPU) — kein ADR nötig

## Report-Back

`backend/photofant/inference/` angelegt:
- `interfaces.py` — `Tagger`, `Captioner`, `Embedder`, `FaceEngine` (Protocols), `TagScore`
- `session_manager.py` — `SessionManager` (lazy load, Idle-Eviction, DML→CUDA→CPU-Detection, ThreadPoolExecutor-Singleton)
- `preprocessing.py` — `preprocess_for_wd14`, `preprocess_for_clip`, `preprocess_for_florence` + Primitives
- `__init__.py` — öffentliche API

`queue.py`: `JobKind` um `TAGGING`, `CAPTIONING`, `EMBEDDING`, `HEURISTICS` erweitert.
`main.py`: `session_manager.evict_all()` im Shutdown-Hook.
`pyproject.toml`: `onnxruntime>=1.20`, `numpy>=1.26` als Core-Dependencies.
