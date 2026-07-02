# P19 — Inference Session Pool (Option B: mehrere Worker pro Modelltyp)

**Status:** Freigegeben, in Umsetzung (freigegeben 2026-07-02)
**Voraussetzung erfüllt:** Option A (dedizierte Worker pro Modelltyp, `queue.py`) ist bereits
im Code — `_tagging_worker`/`_captioning_worker` laufen je einzeln.

## Ziel

Heute läuft je genau ein WD14- (Tagging) und ein Florence2-Worker (Captioning). Mit Session
Pool: N WD14-Worker + M Captioning-Worker parallel, konfigurierbar über die Einstellungen —
beschleunigt große Import-Batches.

## Warum das nicht trivial ist

Ein ONNX `InferenceSession`-Objekt ist nicht re-entrant — zwei Threads dürfen nicht gleichzeitig
`session.run()` auf derselben Session-Instanz aufrufen. Heute ist das safe, weil pro Modelltyp
nur **ein** Worker-Task existiert und `_run_tagging`/`_run_caption_with_preset` über
`asyncio.to_thread` läuft — es ist also immer nur ein Thread gleichzeitig unterwegs. Sobald
mehrere Worker-Tasks pro Typ existieren, laufen mehrere `to_thread`-Aufrufe parallel und würden
sich dieselbe gecachte Session teilen (`SessionManager.acquire_session` gibt heute für einen
`model_path` immer dieselbe Instanz zurück — der `refcount` dient nur der Idle-Eviction, nicht
dem Ausschluss). Das ist der Kern von Phase 1.

## Kontrakt (Schnittstellen zwischen den Phasen)

**Backend — `photofant/inference/session_manager.py`** (neu, zusätzlich zu bestehendem API):

```python
def acquire_exclusive_session(self, model_path: str, pool_size: int) -> ort.InferenceSession:
    """Blockierend: gibt eine Session zurück, die exklusiv diesem Thread gehört.
    Lädt bis zu `pool_size` Instanzen für model_path, blockiert danach bis eine frei wird."""

def release_exclusive_session(self, model_path: str, session: ort.InferenceSession) -> None:
    """Gibt eine per acquire_exclusive_session geliehene Session in den Pool zurück."""
```

Bestehende `acquire_session(model_path)` / `release_session(model_path)` bleiben **unverändert**
— sie bedienen weiterhin CLIP, Buffalo-L und `media/ops.py`, die je nur einen Worker haben und
keinen Pool brauchen. Zwei getrennte Methodennamen, damit niemand versehentlich die
Singleton-Semantik mit der Pool-Semantik mischt.

**Settings** (`photofant/settings.py`, Default `1`, Range `1–4` clientseitig geclampt wie bei
allen anderen Schwellwert-Slidern):

```json
{ "tagging_workers": 1, "captioning_workers": 1 }
```

**`vram.py`** (neu):

```python
def suggest_tagging_workers(vram_gb: float) -> int: ...
def suggest_captioning_workers(vram_gb: float) -> int: ...
```

**API — bestehenden Endpoint erweitern, keinen neuen bauen** (Abweichung von der ursprünglichen
Skizze, siehe Deviations unten): `GET /api/models/vram` liefert zusätzlich

```json
{ "suggested_tagging_workers": 2, "suggested_captioning_workers": 1 }
```
(`null` wenn keine GPU erkannt wurde — analog zu `gpu.vram_gb`).

**Frontend — `ProcessingConfig`** (`frontend/src/app/models/config.model.ts`): neue Felder
`taggingWorkers: number`, `captioningWorkers: number` (Default `1`), gemappt über
`PROCESSING_CONFIG_KEY_MAP` auf `tagging_workers`/`captioning_workers`.

## Phasen

| # | Phase | Rating | Status |
|---|---|---|---|
| 1 | [SessionManager: Pool statt Singleton](phase-1-session-pool.md) | heikel | complete (UI-Smoke offen) |
| 2 | [Settings + N-Worker-Loop in queue.py](phase-2-settings-queue-workers.md) | standard | complete (Manuelle Smokes offen) |
| 3 | [VRAM-Budget-Rechner + API-Erweiterung](phase-3-vram-budget-api.md) | mechanisch | pending |
| 4 | [Frontend: Worker-Slider in Verarbeitung](phase-4-frontend-slider.md) | standard | pending |

## Finale Akzeptanzkriterien (Smoke-Checkliste, User prüft am Plan-Ende)

1. In Einstellungen → Verarbeitung stehen zwei neue Slider „Tagging-Worker" und
   „Caption-Worker" (Range 1–4), je mit „Empfohlen: N" basierend auf der erkannten GPU.
2. Tagging-Worker auf 2 stellen, App neu starten, einen Import mit mehreren Bildern anstoßen →
   im Job-Dock laufen zwei TAGGING-Jobs sichtbar gleichzeitig (nicht strikt nacheinander).
3. Keine Abstürze/Hänger bei gleichzeitigem Tagging + Captioning + Face (Face muss weiterhin
   erst nach Tagging+Captioning für dasselbe Bild starten — unverändert durch `face_pipeline.py`).
4. Worker-Wert auf einen absichtlich zu hohen Wert stellen (z.B. 4 auf einer kleinen GPU) →
   bei einem CUDA-OOM erscheint eine lesbare Fehlermeldung im Job-Dock, kein stiller Crash.

## Deviations vom ursprünglichen Backlog-Konzept

- **Kein neuer Endpoint** `GET /api/settings/hardware-info` — der existierende
  `GET /api/models/vram` liefert GPU-Name + VRAM bereits (für die Modelle-Seite) und wird um
  die zwei `suggested_*`-Felder erweitert statt dupliziert.
- **Zwei Methodennamen statt Overload** (`acquire_exclusive_session`/`release_exclusive_session`
  statt eines optionalen Parameters an den bestehenden Methoden) — verhindert stille
  Verwechslung zwischen Singleton- und Pool-Pfad in den unveränderten Adaptern (CLIP,
  Buffalo-L, `media/ops.py`).

## Bekannte, bewusst nicht angefasste Alt-Stelle

`SessionManager._executor`/`.executor`-Property (Zeile 122-125 in `session_manager.py`) hat
aktuell **keinen einzigen Aufrufer** — die heutige Thread-Sicherheit kommt aus „ein Worker-Task
pro Modelltyp", nicht aus dem eigenen Executor. Bleibt in P19 unangetastet (kein Scope-Teil),
aber falls es beim Lesen auffällt: kein Bug, nur totes Gewebe aus einer früheren Iteration.

## Follow-ups (nicht Teil von P19)

- Echter GPU-Parallelbetrieb (CUDA Streams / ONNX `cuda_stream`-Option) — der aktuelle Ansatz
  überlappt nur CPU-Preprocessing/DB-I/O, GPU-Kernel serialisieren intern weiter.

## Bottom-Sektionen (beim Archivieren füllen)

**Summary:** —
**Files touched:** —
**Commits:** —
**Follow-ups:** —
