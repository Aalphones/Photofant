# Phase 1 — GGUF-Runtime + Adapter + VRAM-Koordination

**Komplexität:** heikel (zweite Inferenz-Runtime, VRAM-Concurrency, Architektur-Entscheidung ADR-029) · **Status:** complete

## Kontext (lesen, bevor du baust)
- [inference/generative_engine.py](../../../backend/photofant/inference/generative_engine.py) — das torch-Vorbild: `load_transformers_model`, `evict_idle`, `unload`, `_evict_locked`, das `_PipelineEntry`-Muster mit `last_used`, das `threading.Lock`. Die GGUF-Engine spiegelt diese **Form**, nicht den Inhalt.
- [inference/adapters/gemma.py](../../../backend/photofant/inference/adapters/gemma.py) — der torch-Adapter; `GemmaGgufAdapter` spiegelt seine Struktur (`__init__(manifest_id, model_dir)`, `model_id`-Property, `generate`, `resolve_*`-Funktion).
- [inference/interfaces.py:108](../../../backend/photofant/inference/interfaces.py#L108) — `TextGenerator`-Protocol, der einzuhaltende Vertrag. **Und [interfaces.py:82](../../../backend/photofant/inference/interfaces.py#L82) `TextEmbedder(Embedder)`** — das exakte Muster für die neue `VisionTextGenerator(TextGenerator)`-Erweiterung (Fähigkeit per `isinstance` prüfbar, nicht blind aufgerufen).
- [main.py:55-62](../../../backend/photofant/main.py#L55) (Idle-Loop) und [main.py:102](../../../backend/photofant/main.py#L102) (Shutdown).
- `backend/pyproject.toml` Zeilen 29-35 — die `generative`-Extra-Group als Vorbild für eine neue Group.
- Convention: [docs/conventions/python.md](../../../docs/conventions/python.md).

## Architektur-Entscheidung (fällt hier → ADR-029)
**VRAM-Invariante:** genau ein Heavy-Modell resident über beide Runtimes.
**Gewählter Weg — gegenseitiges Cross-Unload (kein abstrakter Arbiter):**
- `GgufEngine.load(...)` ruft **vor** dem `Llama(...)`-Konstruktor `generative_engine.unload()` (torch-Slot leeren) — lazy import innerhalb der Methode gegen Import-Zyklus.
- `GenerativeEngine.load_transformers_model(...)` ruft **vor** dem Laden `gguf_engine.unload()` — ebenfalls lazy import. (Das ist die **einzige** Zeile, die an der bestehenden Engine geändert wird.)
- Beide Runtimes entladen unabhängig per `evict_idle`.

**Alternative (verworfen):** ein `vram_arbiter`-Modul mit registrierten Unload-Callbacks. Sauberer ab **drei** Runtimes, aber für genau zwei ist es Abstraktion ohne Gegenwert — zwei gerichtete Aufrufe sind Chesterton-freundlicher und weniger Code. In ADR-029 als betrachtete Option festhalten.

## AK der Phase
- [x] `from llama_cpp import Llama` importiert in der neuen Extra-Group; fehlt die Dependency, degradiert `resolve_gemma_gguf` sauber zu `None` (analog `check_generative_available`), kein harter Crash.
- [x] `GgufEngine` hält genau ein `Llama`-Objekt resident, mit `last_used`, `threading.Lock`, `evict_idle(timeout)`, `unload()` — Form gespiegelt von `GenerativeEngine`.
- [x] **Vision-Naht in der Engine:** `GgufEngine.load(...)` nimmt einen **optionalen** `mmproj_path: str | None = None`. Ist er gesetzt, wird das `Llama`-Objekt mit dem passenden Vision-Chat-Handler + `clip_model_path=mmproj_path` konstruiert; ist er `None`, lädt reiner Text (unverändert). Konkreter Handler: `llama_chat_format.Gemma3ChatHandler` — Import in `try/except ImportError`; fehlt er in der installierten Version, `mmproj_path` ignorieren + **Warnung loggen** (Text läuft weiter) — die Naht bleibt korrekt, siehe README-Risiko.
- [x] **`VisionTextGenerator(TextGenerator)`** in `interfaces.py` definiert (Muster `TextEmbedder`): `generate_with_image(image: np.ndarray, prompt: str, *, system, max_new_tokens) -> str`. **Kein** Aufrufer nutzt es in dieser Phase.
- [x] `GemmaGgufAdapter` erfüllt `TextGenerator`: `generate` faltet `system` in den User-Turn (Gemma kennt keine system-Rolle, wie [gemma.py:46-48](../../../backend/photofant/inference/adapters/gemma.py#L46)) und nutzt llama.cpp's `create_chat_completion` (nutzt das eingebettete Chat-Template des GGUF).
  **Deviation vom Wortlaut:** statt „derselbe Adapter erfüllt zusätzlich VisionTextGenerator" per Instanz-Flag gibt es **zwei Klassen** — `GemmaGgufAdapter` (text-only) und `GemmaGgufVisionAdapter(GemmaGgufAdapter)` (zusätzlich `generate_with_image`). Grund: `isinstance`-Prüfung auf `Protocol` ist rein strukturell (Methode vorhanden ja/nein) — ein Instanz-Flag hätte `isinstance(x, VisionTextGenerator)` für **jede** Instanz `True` gemacht, unabhängig davon, ob ein mmproj gebunden ist. Zwei Klassen (Muster `CLIPEmbedder`/`DINOv2Embedder`, exakt wie im README für `TextEmbedder` referenziert) erhalten die eigentlich gewollte Semantik: die Fähigkeit spiegelt den Bind, nicht nur einen Zustand. `resolve_gemma_gguf` wählt die Klasse anhand des `mmproj`-Eintrags in `ModelRegistry.components`.
- [x] Cross-Unload in **beide** Richtungen aktiv; die VRAM-Invariante hält strukturell (Code-Pfad verifiziert — echte Messung per `nvidia-smi` ist Smoke #2, User).
- [x] Idle-Loop [main.py:62](../../../backend/photofant/main.py#L62) ruft zusätzlich `gguf_engine.evict_idle(ai_idle_timeout)`; Shutdown [main.py:104](../../../backend/photofant/main.py#L104) ruft zusätzlich `gguf_engine.unload()`.

## Checkliste
- [x] `backend/pyproject.toml`: neue Extra-Group `gemma-gguf = ["llama-cpp-python>=0.3"]`. Im Kopf-Kommentar der Group den CUDA-Wheel-Install-Weg als Notiz (Plan B für Smoke #1).
- [x] `interfaces.py`: `VisionTextGenerator(TextGenerator)`-Protocol ergänzt (Muster `TextEmbedder`).
- [x] `inference/gguf_engine.py` neu: `GgufEngine` (Lifecycle, optionaler `mmproj_path`) + Modul-Singleton `gguf_engine` + `check_gguf_available()`.
- [x] `inference/adapters/gemma_gguf.py` neu: `GemmaGgufAdapter` + `GemmaGgufVisionAdapter` (s.o. Deviation) + `resolve_gemma_gguf(manifest_id) -> GemmaGgufAdapter | None`.
- [x] `generative_engine.py`: die eine Cross-Unload-Zeile in `load_transformers_model` (lazy import `gguf_engine`).
- [x] `main.py`: Idle-Loop + Shutdown um den GGUF-Slot erweitert.
- [x] `cd backend && uv run ruff check photofant/inference/gguf_engine.py photofant/inference/adapters/gemma_gguf.py photofant/inference/interfaces.py photofant/inference/generative_engine.py photofant/main.py && uv run mypy photofant/inference/gguf_engine.py photofant/inference/adapters/gemma_gguf.py` grün bis auf einen erwarteten Rest — siehe Report-Back.

## Report-Back

**ruff:** grün auf allen geänderten/neuen Dateien. `ruff check .` (ganzes Repo) zeigt 7 **vorbestehende** Fehler in unberührten Dateien (Alembic-Migrationen, `api/assets.py`, `inference/tools.py`, `jobs/comfyui_run_job.py`) — keiner davon durch diese Phase eingeführt, per `git status` verifiziert.

**mypy:** `gguf_engine.py` + `gemma_gguf.py` zeigen genau **einen** Fehler — `Cannot find implementation or library stub for module named "llama_cpp"` (import-not-found), weil `llama-cpp-python` in diesem Dev-Venv nicht installiert ist. Das ist **derselbe Musterfehler**, den `generative_engine.py` isoliert geprüft für `torch`/`transformers` zeigt (2 Fehler, selbe Ursache: optionale Extra nicht installiert) — kein neues Problem, sondern die etablierte Konvention für optionale Runtime-Dependencies in diesem Projekt. Wird grün, sobald die CUDA-Wheel-Installation (Smoke-Checkliste #1) gelaufen ist.

**uv.lock:** hat sich automatisch aktualisiert (neue Extra-Group `gemma-gguf` mit `llama-cpp-python==0.3.34` aufgelöst) — das Paket selbst ist **nicht** installiert (nur die Lock-Auflösung; Installation ist der Smoke-Test-Schritt).

**Import-Zyklus geprüft:** `photofant.main`, `gguf_engine`, `gemma_gguf`, `generative_engine` importieren sich sauber ohne Zyklus (verifiziert per Direktimport — beide `check_*_available()` melden korrekt `not_installed`).

**Nicht Teil dieser Phase, aber aufgefallen:** `GenerativeEngine.load_transformers_model` (und damit jeder Adapter, der es aufruft — `gemma.py`, `qwen_vl.py`, `joycaption.py`) evict't und lädt bei **jedem** `generate()`/`caption()`-Aufruf neu, auch wenn dasselbe Modell schon resident ist — kein „bereits geladen"-Check. Für ein 4-12B-Modell ist das ein spürbarer Perf-Hit pro Aufruf. `GgufEngine` spiegelt dieses Verhalten bewusst (Form-Vorgabe der Phase), führt also denselben Effekt für GGUF neu ein. Separates Ticket wert, nicht in dieser Phase angefasst (Scope: reine VRAM-Koordination zwischen zwei Runtimes, nicht Reload-Vermeidung innerhalb einer Runtime).

