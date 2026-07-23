# ADR-037 — Modell-Inferenz-Jobs laufen in einem eigenen Worker-Prozess

**Status:** Akzeptiert — 2026-07-23
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
komplett in den Worker-Prozess um (ab Phase 2/3 — Phase 1 migriert nur den DEMO-Job als
Beweis-Fall für die IPC-Strecke). I/O-Jobs (Import, Export, Thumbnail, Backup, Download,
ComfyUI-Run) bleiben im API-Prozess — sie sind nicht GIL-belastend.

Phase 1 (dieser Stand): `backend/photofant/worker/` (protocol.py, dispatch.py, process.py) plus
Remote-Proxy in `jobs/queue.py` (`enqueue_remote()`, `_remote_status_forwarder()`). Der
API-Prozess startet den Worker-Prozess in `main.py::_lifespan` vor `job_queue.start()` und
stoppt ihn beim Shutdown per Poison-Pill (Timeout + `terminate()`-Fallback).

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
- Der API-seitige `JobQueue`-Rückkanal (`_remote_status_forwarder`) liest `multiprocessing.Queue`
  mit einem 1s-Timeout statt unbegrenzt blockierend — sonst könnte `JobQueue.stop()` beim
  Shutdown nie abbrechen, weil ein bereits laufender Executor-Blocking-Call sich per
  `asyncio.Task.cancel()` nicht unterbrechen lässt.
