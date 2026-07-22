# Phase 1 — Fundament: IPC-Brücke + Worker-Skeleton, ADR-033

**Komplexität:** heikel (neue Prozess-Grenze, neuer Transport-Mechanismus, Architektur-ADR).

## Kontext (lesen vor dem Start)

- [backend/photofant/jobs/queue.py](../../../backend/photofant/jobs/queue.py) — die bestehende
  `JobQueue`-Klasse zieht als Ganzes (unverändert) in den Worker-Prozess um. Diese Phase baut nur
  den Transport davor, ändert an der Klasse selbst noch nichts.
- [backend/photofant/main.py](../../../backend/photofant/main.py) Zeile 57-106 — `_lifespan`,
  `_idle_eviction_loop`. Der Worker-Prozess wird hier gestartet/gestoppt, symmetrisch zu
  `job_queue.start()`/`job_queue.stop()`.
- [backend/photofant/api/jobs.py](../../../backend/photofant/api/jobs.py) — `run_demo_job`,
  `_demo_coro`. Der DEMO-Job ist der Beweis-Fall dieser Phase (kein GPU, keine Modelle, nur ein
  5-Schritte-`asyncio.sleep`-Loop) — er zeigt, dass IPC + Status-Rückkanal funktionieren, ohne dass
  echte Inferenz-Migration schon nötig wäre.
- README „Kontrakt" — Nachrichtenformen (`JobRequest`, `JobStatusMessage`,
  `PipelineSignalMessage`) und die Dispatch-Tabelle-Idee sind dort vorgegeben, nicht neu erfinden.
- `~/.claude/sync/knowledge/topics/windows.md` (falls beim Umsetzen auf Windows-Eigenheiten
  gestoßen wird — `multiprocessing` mit `spawn` hat eigene Fallstricke, siehe Aufgabe 4).

## Aufgabe 1 — Protokoll-Modul

Neue Datei `backend/photofant/worker/__init__.py` (leer, macht `worker` zum Package) und
`backend/photofant/worker/protocol.py` — Inhalt exakt wie im README „Kontrakt" spezifiziert
(`JobRequest`, `JobStatusMessage`, `PipelineSignalMessage`).

## Aufgabe 2 — Worker-Prozess-Entry-Point

Neue Datei `backend/photofant/worker/process.py`. Der Worker bekommt eine **eigene** `JobQueue`-
Instanz (Import aus `jobs.queue`, nicht die globale API-seitige) und eine Listener-Coroutine, die
`JobRequest`-Nachrichten von der Request-Queue liest und daraus per Dispatch-Tabelle
(`worker/dispatch.py`, Aufgabe 3) einen `coro_factory` baut, den die lokale `JobQueue.enqueue()`
entgegennimmt — exakt wie heute, nur dass der `coro_factory` jetzt aus einem Payload-Dict
rekonstruiert wird statt als Closure von einer API-Route zu kommen.

Symmetrisch dazu: die lokale `JobQueue.subscribe()` liefert `JobStatus`-Updates, die eine zweite
Coroutine 1:1 in `JobStatusMessage`s übersetzt und auf die Status-Queue schreibt.

```python
"""Worker-Prozess-Entry-Point — läuft in einem eigenen OS-Prozess (multiprocessing.Process),
NICHT im API-Prozess. Bekommt zwei multiprocessing.Queue-Objekte beim Start übergeben und
startet darin sein eigenes asyncio-Event-Loop mit einer eigenen JobQueue-Instanz.

WICHTIG (Windows `spawn`): Diese Funktion ist der komplette Eintrittspunkt des Kindprozesses —
sie darf keine Seiteneffekte voraussetzen, die nur im API-Prozess passiert sind (z.B. FastAPI-
App-Erzeugung). Alle Imports hier sind Kindprozess-lokal und frisch.
"""
from __future__ import annotations

import asyncio
import logging
import multiprocessing as mp

from photofant.jobs.queue import JobQueue
from photofant.worker.dispatch import JOB_HANDLERS
from photofant.worker.protocol import JobRequest, JobStatusMessage

log = logging.getLogger(__name__)


async def _request_listener(worker_queue: JobQueue, request_queue: "mp.Queue[JobRequest | None]") -> None:
    loop = asyncio.get_running_loop()
    while True:
        request = await loop.run_in_executor(None, request_queue.get)  # blocking get, im Executor-Thread
        if request is None:  # Poison Pill — sauberes Herunterfahren
            return
        handler = JOB_HANDLERS.get(request.kind)
        if handler is None:
            log.error("Worker: kein Handler für JobKind %r — Auftrag verworfen", request.kind)
            continue
        await worker_queue.enqueue(
            kind=request.kind,
            label=request.label,
            coro_factory=lambda status, payload=request.payload, run=handler: run(status, payload),
        )


async def _status_forwarder(worker_queue: JobQueue, status_queue: "mp.Queue[JobStatusMessage]") -> None:
    subscriber = worker_queue.subscribe()
    while True:
        status = await subscriber.get()
        status_queue.put(JobStatusMessage(
            type="job_status", job_id=status.id, progress=status.progress,
            state=status.state.value, error=status.error, result=status.result,
        ))


async def _run_worker(request_queue: "mp.Queue[JobRequest | None]", status_queue: "mp.Queue[JobStatusMessage]") -> None:
    worker_queue = JobQueue()
    worker_queue.start()
    log.info("Worker-Prozess bereit")
    await asyncio.gather(
        _request_listener(worker_queue, request_queue),
        _status_forwarder(worker_queue, status_queue),
    )


def run_worker_process(request_queue: "mp.Queue[JobRequest | None]", status_queue: "mp.Queue[JobStatusMessage]") -> None:
    """Synchroner Einstiegspunkt für `multiprocessing.Process(target=...)`."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(_run_worker(request_queue, status_queue))
```

Das ist ein **Gerüst**, kein Endzustand — insbesondere `PipelineSignalMessage` fließt hier noch
nicht (kommt in Phase 2, sobald der erste Job mit einer Pipeline-Abhängigkeit migriert). Ziel
dieser Phase ist der bewiesene Rundlauf, nicht Vollständigkeit.

## Aufgabe 3 — Dispatch-Tabelle (leer, außer DEMO)

Neue Datei `backend/photofant/worker/dispatch.py`:

```python
from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from photofant.jobs.queue import JobKind, JobState, JobStatus

async def _demo_handler(status: JobStatus, _payload: dict[str, Any]) -> None:
    import asyncio
    steps = 5
    for step in range(1, steps + 1):
        await asyncio.sleep(1.0)
        from photofant.jobs.queue import job_queue as _unused  # Platzhalter, siehe Hinweis unten
        status.progress = step / steps
        status.state = JobState.RUNNING

JOB_HANDLERS: dict[JobKind, Callable[[JobStatus, dict[str, Any]], Coroutine[Any, Any, None]]] = {
    JobKind.DEMO: _demo_handler,
}
```

Hinweis beim Umsetzen: der `_demo_handler` darf **nicht** `job_queue.update()` aus dem API-Prozess
aufrufen (das ist ein anderer Prozess) — er mutiert `status` direkt, die Worker-lokale `JobQueue`
liest denselben `JobStatus`-Objekt-Zustand danach über ihre eigene `_notify`-Kette aus. Beim
Implementieren gegen `jobs/queue.py::_run_job` gegenchecken, wie Fortschritt heute innerhalb einer
Coroutine gemeldet wird, und das Muster 1:1 übernehmen statt zu improvisieren.

## Aufgabe 4 — API-seitiger Remote-Proxy

`backend/photofant/jobs/queue.py` bekommt eine kleine Erweiterung: eine Menge
`_REMOTE_KINDS: frozenset[JobKind]` (startet mit `{JobKind.DEMO}`, wächst in Phase 2/3), und
`JobQueue.enqueue()` bekommt einen zusätzlichen Zweig — landet der `kind` in `_REMOTE_KINDS`,
wird statt lokal einzureihen ein `JobRequest` auf eine Request-Queue geschrieben (Referenz auf die
`multiprocessing.Queue`-Instanz, die `main.py` beim Start injiziert — z.B. über eine
`set_remote_transport(request_queue, status_queue)`-Methode, aufgerufen bevor `job_queue.start()`
läuft). Der `JobStatus` wird trotzdem lokal in `self._jobs` angelegt und benachrichtigt (wie
heute) — nur die Ausführung passiert woanders.

Eine neue Hintergrund-Coroutine (gestartet in `JobQueue.start()`, analog zu `_worker`) liest die
Status-Queue leer und ruft für jede eingehende `JobStatusMessage` `self.update(...)` bzw.
`self.set_result(...)` auf dem passenden, bereits existierenden `JobStatus` (Lookup über
`job_id` in `self._jobs`) auf. Für's Frontend ändert sich dadurch **nichts** — `snapshot()`,
`subscribe()`, der SSE-Stream in `api/jobs.py` bleiben exakt wie sie sind.

⚠️ Diese Methode muss vorsichtig mit `coro_factory` umgehen: für `_REMOTE_KINDS` gibt es keinen
lokal auszuführenden `coro_factory` mehr — der Aufrufer (z.B. `run_demo_job` in `api/jobs.py`)
übergibt stattdessen ein Payload-Dict. Sauberste Lösung: `enqueue()` bekommt einen neuen,
optionalen Parameter `payload: dict[str, Any] | None = None`, der nur für `_REMOTE_KINDS` Pflicht
ist (bei lokalen Kinds bleibt `coro_factory` Pflicht wie bisher) — beim Umsetzen zwei getrennte,
klar benannte Enqueue-Pfade erwägen (`enqueue()` für lokal, `enqueue_remote()` für Remote), statt
einen Parameter mit wechselnder Pflicht zu bauen, der beim Lesen verwirrt.

`api/jobs.py::run_demo_job` entsprechend umstellen: statt `coro_factory=_demo_coro` ein leeres
Payload-Dict übergeben (`{}` — der Demo-Handler braucht keine Eingabe).

## Aufgabe 5 — Prozess-Lifecycle in `main.py`

`_lifespan` bekommt zwei neue Zeilen vor `job_queue.start()`:

```python
import multiprocessing as mp
from photofant.worker.process import run_worker_process

_request_queue: mp.Queue = mp.Queue()
_status_queue: mp.Queue = mp.Queue()
job_queue.set_remote_transport(_request_queue, _status_queue)
worker_process = mp.Process(target=run_worker_process, args=(_request_queue, _status_queue), daemon=True)
worker_process.start()
```

Beim Shutdown (nach `await job_queue.stop()`): Poison-Pill auf die Request-Queue (`None`),
`worker_process.join(timeout=5)`, falls der Prozess dann noch lebt `worker_process.terminate()`.
Crash-Erkennung (Prozess stirbt unerwartet, Auto-Respawn) ist **nicht** Teil dieser Phase —
Phase 4 baut das robust. Hier reicht: stirbt der Worker, wird das laut geloggt (Health-Check-
Grundgerüst), die API läuft weiter, ohne dass neue Jobs überhaupt versucht werden zu senden.

## Aufgabe 6 — Windows-`spawn`-Check

Vor dem restlichen Umsetzen verifizieren: `multiprocessing.get_start_method()` liefert auf diesem
Windows-Rechner `"spawn"` (Standard, nicht `"fork"` — Windows kennt `fork` nicht). Der
Modul-Level-Code in `worker/process.py` darf deshalb **keine** Annahme treffen, dass er Zustand
vom Eltern-Prozess erbt (er tut es nicht — jeder Import läuft frisch). Falls das Skript nicht
unter einem `if __name__ == "__main__":`-Guard im Hauptmodul läuft (bei `uv run uvicorn ...`
normalerweise unkritisch, da der Uvicorn-Reloader selbst schon einen eigenen Prozess-Start-Pfad
hat) — beim ersten echten Start beobachten, ob `multiprocessing` mit einer
`RuntimeError`/Endlos-Neustart-Schleife reagiert; falls ja, Guard ergänzen.

## Aufgabe 7 — ADR-033

Nummer verifizieren (`grep -rn "ADR-0[3-9][0-9]" docs/planning/` — letzte bekannte Nummer war 032,
falls seither ein anderer Plan entstanden ist, hochzählen). Neue Datei
`docs/decisions/033-ml-jobs-worker-prozess.md`:

```markdown
# ADR-033 — Modell-Inferenz-Jobs laufen in einem eigenen Worker-Prozess

**Status:** Akzeptiert — 2026-07-22
**Querverweise:** [017](017-inference-session-pool.md) (Pool-Verwaltung bleibt, zieht nur um)

## Kontext
Alle Jobs nutzen korrekt `asyncio.to_thread` — das verhindert, dass der Event-Loop per `await`
blockiert, aber Python's GIL ist prozessweit. CPU-schwere Inferenz (ONNX-Beam-Search, torch
`generate()`, NumPy) in einem Worker-Thread hungert den Main-Thread trotzdem aus. Beobachtet:
API-Requests (Lightbox) blockieren, während Jobs laufen — reproduziert auch mit dem leichten
Florence-2-Base-Captioner, nicht nur mit schweren Instruct-Modellen.

## Entscheidung
Alle Modell-Inferenz-Jobs (Tagging, Captioning, Embedding, Heuristics, Classification, Face,
Clustering, Dupe-Scan) laufen in einem dauerhaften, separaten OS-Prozess. Kommunikation über
zwei `multiprocessing.Queue`s (Auftrag rein, Status/Ergebnis raus) — kein Message-Broker, keine
neue Abhängigkeit. Der Modell-Cache (`session_manager`, `generative_engine`, `gguf_engine`) zieht
komplett in den Worker-Prozess um. I/O-Jobs (Import, Export, Thumbnail, Backup, Download,
ComfyUI-Run) bleiben im API-Prozess — sie sind nicht GIL-belastend.

## Betrachtete Optionen
- **`sys.setswitchinterval()` reduzieren** — mildert Symptome, behebt aber nicht die Ursache;
  jede zusätzliche CPU-schwere Inferenz-Änderung müsste erneut gegen dasselbe Problem antreten.
  Verworfen als alleinige Lösung.
- **`ProcessPoolExecutor` statt dauerhaftem Prozess** — würde bei jedem Job das Modell neu auf die
  GPU laden (Sekunden bis zig Sekunden Zusatzkosten pro Bild). Verworfen — der Prozess muss
  dauerhaft laufen, damit der Modell-Cache warm bleibt.
- **Mehrere Worker-Prozesse (getrennt nach Modelltyp)** — echte Parallelität zwischen z.B. Tagging
  und Captioning, aber mehr IPC-Komplexität für ein Problem, das mit einem Prozess schon gelöst
  ist. Verschoben auf einen Folge-Plan, falls der eine Worker-Prozess selbst zum Nadelöhr wird.

## Konsequenzen
- API-Prozess kann durch keine noch so schwere Inferenz-Last mehr ausgehungert werden — GIL-
  Kontention ist per Definition auf den Worker-Prozess begrenzt.
- Neue Fehlerklasse: der Worker-Prozess kann unabhängig abstürzen. Muss erkannt und behandelt
  werden (Phase 4), sonst bleiben Jobs für immer in `running` stecken.
- Jeder migrierte Job braucht ein serialisierbares Payload statt einer Closure — kleiner,
  mechanischer Umbau pro Job (siehe Plan-README „Wichtige Funde").
```

## AK dieser Phase

- [ ] `backend/photofant/worker/` existiert mit `protocol.py`, `process.py`, `dispatch.py`.
- [ ] Worker-Prozess startet beim Backend-Start automatisch (Log-Zeile „Worker-Prozess bereit").
- [ ] `POST /api/jobs/demo` läuft über die neue IPC-Strecke — Fortschritt (5 Schritte, 1×/Sekunde)
      kommt weiterhin live im Job-Dock an, ununterscheidbar vom bisherigen Verhalten.
- [ ] Backend-Shutdown (Strg+C) beendet den Worker-Prozess mit, kein Zombie-Prozess danach.
- [ ] Worker-Prozess im Task-Manager gezielt beendet, während der Demo-Job läuft: API bleibt
      erreichbar (z.B. `GET /api/health` antwortet weiter), Beweis der Isolation — noch **ohne**
      automatischen Neustart (das ist Phase 4).
- [ ] SQLite-Parallelzugriff geprüft (Konfidenz-Ausweis README Punkt 2): aus beiden Prozessen
      gleichzeitig lesen/schreiben, kein `database is locked`.
- [ ] ADR-033 liegt unter `docs/decisions/033-ml-jobs-worker-prozess.md` (Nummer verifiziert).

## Doc-Updates

- [ ] `docs/code-map.md` — Zeile „Jobs / Queue" ergänzen: neuer Worker-Prozess + `worker/`-Modul.

## Report-Back

_(nach Umsetzung ausfüllen: was abweicht, was die Windows-`spawn`-Startzeit tatsächlich war,
Ergebnis des SQLite-Parallelzugriff-Checks)_
