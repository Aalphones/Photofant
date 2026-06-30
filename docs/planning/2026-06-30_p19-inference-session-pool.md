# P19 — Inference Session Pool (Option B: Gleicher Modelltyp parallel)

**Status:** Backlog  
**Voraussetzung:** Option A (P19 baut auf der dedizierten Worker-Architektur aus queue.py auf)

## Ziel

Mehrere Instanzen desselben Modells (WD14 oder Florence2) gleichzeitig laufen lassen,
um große Import-Batches weiter zu beschleunigen. Heute läuft je ein WD14- und ein
Florence2-Worker (Option A). Mit Session Pool: N WD14-Worker + M Florence2-Worker.

## Warum noch nicht

Ein ONNX `InferenceSession`-Objekt ist nicht re-entrant — zwei Threads können nicht
gleichzeitig `session.run()` auf derselben Session aufrufen. Option A umgeht das durch
je einen dedizierten Worker pro Modelltyp (ein Worker = ein Thread = ein Session-Zugriff
zur Zeit). Für N Worker desselben Typs braucht man N separate Session-Instanzen.

## Was zu bauen ist

### 1. `SessionManager`: Session Pool statt Singleton

Aktuell: `_sessions: dict[str, _SessionEntry]` — eine Session pro Model-Pfad.

Neu: `_sessions: dict[str, list[_SessionEntry]]` — Pool von N Sessions pro Model-Pfad.

```python
def acquire_exclusive_session(self, model_path: str) -> ort.InferenceSession:
    """Blockierend: gibt eine Session zurück, die exklusiv diesem Thread gehört."""
    # Wähle eine freie Session (refcount == 0) oder lade eine neue.

def release_session(self, model_path: str, session: ort.InferenceSession) -> None:
    """Gibt die Session zurück in den Pool."""
```

Die Adapter (WD14, Florence2) müssen auf `acquire_exclusive_session` umgestellt werden.

### 2. Settings: `tagging_workers` und `captioning_workers`

```json
{
  "tagging_workers": 1,
  "captioning_workers": 1
}
```

Default: 1 (entspricht heutigem Verhalten nach Option A).

### 3. `queue.py`: N Worker pro Typ

```python
# start():
for _ in range(settings["tagging_workers"]):
    asyncio.create_task(self._tagging_worker())
for _ in range(settings["captioning_workers"]):
    asyncio.create_task(self._captioning_worker())
```

### 4. VRAM-Budget-Rechner (`vram.py`)

```python
def suggest_tagging_workers(vram_gb: float) -> int:
    # WD14 SwinV2-v3: ~450 MB pro Session-Instanz
    # + ~200 MB Aktivierungen pro gleichzeitigem Lauf
    available = vram_gb - 1.5  # OS + andere Modelle
    return max(1, min(4, int(available / 0.65)))

def suggest_captioning_workers(vram_gb: float) -> int:
    # Florence-2-base: ~1.5 GB pro Session-Instanz (4 ONNX-Sessions)
    # + ~300 MB Aktivierungen
    available = vram_gb - 0.5  # OS
    return max(1, min(4, int(available / 1.8)))
```

Beispiel RTX 3060 (12 GB):
- WD14: floor(10.5 / 0.65) = 16 → gedeckelt auf 4
- Florence2: floor(11.5 / 1.8) = 6 → gedeckelt auf 4

In der Praxis sinnvoll: max 3, da GPU-Compute (nicht VRAM) zuerst sättigt.

### 5. Settings-UI: Slider in Einstellungen → Bearbeitung

```
Tagging-Worker  [●—————] 1  (Empfohlen: 3 · RTX 3060, 12 GB)
Caption-Worker  [●—————] 1  (Empfohlen: 2 · RTX 3060, 12 GB)
```

API: `GET /api/settings/hardware-info` liefert `{ vram_gb, gpu_name, suggested_tagging_workers, suggested_captioning_workers }`.
Reuse `detect_gpu()` aus `photofant/models/vram.py`.

## Aufwand

- Backend Session Pool: ~2 Tage
- Settings + API: ~0.5 Tage
- Frontend Slider: ~0.5 Tage
- Tests: ~1 Tag

## Risiken

- ONNX Runtime: mehrere Sessions auf demselben CUDA-Device ohne explizite Stream-Trennung
  serialisieren GPU-Kernel intern. Speedup kommt hauptsächlich aus CPU-Überlappung
  (Preprocessing, DB-I/O). Echter GPU-Parallelbetrieb würde CUDA Streams + ONNX
  Session-Options (`cuda_stream`) erfordern — deutlich komplexer.
- VRAM-Überbuchung: Wenn der Nutzer manuell zu viele Worker konfiguriert und das Modell
  nicht in den VRAM passt, crasht OnnxRuntime mit einem CUDA OOM. Muss mit einer
  klaren Fehlermeldung abgefangen werden.
