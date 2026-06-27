# P14 — Job-Queue: Zwei-Spuren + Priorität in Lane 3

**Status:** complete

Die aktuelle Queue hat einen einzigen sequenziellen Worker. Ein laufender Caption-Job
(Florence-2, ONNX, bis zu mehreren Sekunden pro Bild) blockiert jeden nachfolgenden
Job — auch zeitkritische wie Import oder Face-Extraktion.

Ziel: zwei parallele Worker-Lanes + Prioritätswarteschlange für Background-Inferenz,
sodass user-getriggerte Jobs (Import, Export, ComfyUI) nie auf laufende Caption-Jobs warten.

---

## Architektur

```
Spur 1 — parallel (schon da):   DOWNLOAD  →  fire-and-forget asyncio.Task
Spur 2 — main worker:            IMPORT, SCAN, EXPORT, BULK_EDIT, RECONCILE,
                                  THUMBNAIL, THUMBNAIL_REBUILD, REBUILD,
                                  REEVALUATE, RERUN, DEMO, BACKUP
Spur 3 — background worker:      COMFYUI_RUN, UPSCALE, FLUX_EDIT, INPAINT (Prio 10)
                                  FACE (Prio 20)
                                  HEURISTICS (Prio 30)
                                  TAGGING, EMBEDDING (Prio 40)
                                  CLUSTERING, DUPE_SCAN (Prio 50)
                                  CAPTIONING (Prio 60)
```

Spur 2 = `asyncio.Queue` (FIFO wie heute).
Spur 3 = `asyncio.PriorityQueue[tuple[int, int, _Job]]` — (prio, seq, job),
seq = monoton steigender Counter für FIFO innerhalb gleicher Prio.

**Model-Reload-Overhead:** keiner. Der `session_manager` cached ONNX-Sessions 5 min
nach Release (refcount=0). Florence-2 und buffalo_l coexistieren im Cache — Prio-Wechsel
zwischen Caption und Face ist ein reiner dict-Lookup, kein Reload.

---

## Overview

| Phase | Thema | Status |
|---|---|---|
| 1 | Queue-Kern refactorn | complete |
| 2 | Doc-Sync | complete |

---

## Phase 1 — Queue-Kern refactorn

**Datei:** `backend/photofant/jobs/queue.py`

### Checklist

- [ ] `_BACKGROUND_PRIORITY: dict[JobKind, int]` hinzufügen:
  ```python
  _BACKGROUND_PRIORITY: dict[JobKind, int] = {
      JobKind.COMFYUI_RUN: 10,
      JobKind.UPSCALE: 10,
      JobKind.FLUX_EDIT: 10,
      JobKind.INPAINT: 10,
      JobKind.FACE: 20,
      JobKind.HEURISTICS: 30,
      JobKind.TAGGING: 40,
      JobKind.EMBEDDING: 40,
      JobKind.CLUSTERING: 50,
      JobKind.DUPE_SCAN: 50,
      JobKind.CAPTIONING: 60,
  }
  ```
- [ ] `_BACKGROUND_KINDS: frozenset[JobKind]` = `frozenset(_BACKGROUND_PRIORITY)`
- [ ] `JobQueue.__init__`: zweite Queue `_background_queue: asyncio.PriorityQueue[tuple[int, int, _Job]]` + Counter `_bg_seq: int = 0` + `_background_worker_task: asyncio.Task[None] | None = None`
- [ ] `JobQueue.start()`: `_background_worker_task = asyncio.create_task(self._background_worker())`
- [ ] `JobQueue.stop()`: `_background_worker_task` canceln (symmetrisch zu `_worker_task`)
- [ ] `JobQueue.enqueue()`: Routing nach Kind:
  - `_PARALLEL_KINDS` → bleibt fire-and-forget (unverändert)
  - `_BACKGROUND_KINDS` → `_background_queue.put((prio, seq, job))`; seq aus `_bg_seq` (atomar inkrementieren)
  - sonst → `_queue.put(job)` (main worker, unverändert)
- [ ] `JobQueue._background_worker()`: loop über `_background_queue.get()`, `task_done()` aufrufen; Fehler-Handling identisch `_worker()`

---

## Phase 2 — Doc-Sync

### Checklist

- [ ] `docs/code-map.md`: Jobs-Sektion — zwei Worker-Lanes dokumentieren
- [ ] `STATE.md`: P14 als abgeschlossen eintragen, Pointer auf nächsten Plan

---

## Risiken

🟡 **SQLite-Concurrent-Writes:** Spur 2 und 3 schreiben beide in die DB (andere Tabellen/Rows). SQLite WAL serialisiert Schreibzugriffe auf Engine-Ebene — bei Busy-Waits greift der bestehende SQLAlchemy-Timeout. Kein Änderungsbedarf, aber im Auge behalten.

🟡 **Qwen2.5-VL / JoyCaption (heavy captioners):** Diese nutzen nicht den `session_manager`, sondern torch-Singletons. Beim Prio-Wechsel Caption→Face bleiben sie geladen (kein Unload) — kein Overhead, aber VRAM-Belegung bleibt bestehen solange der Prozess läuft.

---

## Archiv-Footer

**Summary:** Dritte Worker-Lane in `jobs/queue.py` ergänzt: Background-Inferenz läuft jetzt
auf einer eigenen `asyncio.PriorityQueue` (Prio 10–60, FIFO via Sequenz-Counter innerhalb
gleicher Prio), parallel zum bestehenden Main-FIFO-Worker. User-getriggerte Jobs warten
nicht mehr hinter laufenden Caption-Jobs.

**Files touched:** `backend/photofant/jobs/queue.py` · `docs/code-map.md`

**Commits:** (siehe `feat(queue)`-Commit für P14)

**Deviations:** Statt die Run-Logik ein drittes Mal zu kopieren, wurde `_run_parallel`
zu einem geteilten `_run_job(status, coro_factory)`-Helfer verallgemeinert, den Main- und
Background-Worker plus die parallelen Tasks gemeinsam nutzen — „identisches Fehler-Handling"
by construction statt drei driftender Kopien. Log-Message dadurch einheitlich `"Job %s failed"`
(vorher unterschied der Parallel-Pfad mit `"Parallel job %s failed"`).

**Follow-ups:** Keine. Risiken (SQLite-Concurrent-Writes, VRAM bei heavy captionern) bleiben
beobachtet, kein Handlungsbedarf.
