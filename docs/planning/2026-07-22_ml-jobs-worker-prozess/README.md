# Worker-Prozess für ML-Inferenz-Jobs

> Alle Modell-Inferenz-Jobs (Tagging, Captioning, Embedding, Heuristics, Classification, Face,
> Clustering, Dupe-Scan) verlassen den API-Prozess und laufen dauerhaft in einem eigenen
> Worker-Prozess. Grund: `asyncio.to_thread` verhindert nur, dass der Event-Loop per `await`
> blockiert — Python's GIL ist aber prozessweit, und CPU-schwere Inferenz in einem Worker-Thread
> hungert den Main-Thread trotzdem aus. Bestätigt am laufenden System: Lightbox/API-Requests
> blockieren, während Jobs laufen — reproduzierbar schon mit dem leichten Florence-2-Base-
> Captioner, nicht nur mit den schweren Instruct-Modellen. I/O-Jobs (Import, Export, Thumbnail,
> Backup, Download, ComfyUI-Run) bleiben im API-Prozess — die sind nicht GIL-belastend.
> *(private, lean — Architektur-Plan: neuer Prozess, neue IPC-Schicht, ein neues ADR.)*

## Phasen

| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Fundament — IPC-Brücke + Worker-Skeleton, ADR-037 | heikel | complete |
| 2 | Erstmigration — Captioning + Tagging | heikel | complete |
| 3 | Rest-Migration — Embedding, Heuristics, Classification, Face, Clustering, Dupe-Scan | standard | pending |
| 4 | Härtung + Cleanup | standard | pending |

## Ziel

Die Lightbox (und jede andere API-Anfrage) bleibt flott, egal was gerade im Hintergrund
verarbeitet wird. Heute gilt Regel 5 aus [AGENTS.md](../../../AGENTS.md#L62) ("Die UI blockiert
nie") nur auf Thread-Ebene — der Code hält sich korrekt daran (`asyncio.to_thread` überall
verifiziert), aber die Garantie reicht nicht, weil der GIL Thread-Grenzen ignoriert. Nach diesem
Plan hält die Garantie auf Prozess-Ebene: der API-Prozess kann gar nicht mehr durch Inferenz-Last
ausgehungert werden, weil die Inferenz in einem komplett anderen Betriebssystem-Prozess läuft.

## Vorgeschichte — was der User entschieden hat

1. **Diagnose bestätigt, nicht nur vermutet.** Vor diesem Plan wurde am Code nachgewiesen: jeder
   Job nutzt `asyncio.to_thread` korrekt (kein vergessenes `await`), der einzige Cross-Thread-Call
   (`face_pipeline.py` → `run_coroutine_threadsafe`) ist Fire-and-Forget statt blockierend, die
   DB-Engine nutzt WAL + echten Pool (keine Serialisierung). Die einzige verbleibende Erklärung
   ist GIL-Kontention zwischen dem Inferenz-Thread und dem Event-Loop-Thread.
2. **Scope bewusst breiter als der ursprüngliche Symptom-Report.** Der User hat live bestätigt,
   dass auch mit Florence-2-Base (dem leichten ONNX-Captioner) und auch mit anderen Jobs in der
   Queue das Problem auftritt — nicht nur mit schweren Instruct-Captionern. Deshalb migrieren
   **alle** Modell-Inferenz-Jobs, nicht nur Captioning.
3. **I/O-Jobs bleiben, wo sie sind.** Import, Export, Thumbnail-Generierung, Backup, Download,
   ComfyUI-Run (reiner HTTP-Call nach außen) sind nicht GIL-belastend — sie warten auf Disk/Netz,
   nicht auf CPU. Migration würde nur Komplexität ohne Nutzen bringen.
4. **Ein Worker-Prozess für alle migrierten Jobs (v1), kein Split nach Modelltyp.** GPU-Kontention
   zwischen z.B. Tagging und Captioning bleibt wie heute über `session_manager`s Pool-Verwaltung
   gelöst — dieser Plan behebt die GIL-Fairness zwischen API und Inferenz, nicht die
   GPU-Warteschlange der Inferenz-Jobs untereinander (siehe „Bewusst draußen").

## Wichtige Funde vor dem Planen

**Der Worker-Prozess ist kein Neubau — er ist ein Umzug.** `jobs/queue.py`s `JobQueue`-Klasse mit
ihren dedizierten Tagging-/Captioning-Workern, der Background-Prioritäts-Queue und der
Pool-Skalierung ist bereits exakt die richtige Maschinerie — sie muss nur in einem anderen
Prozess laufen. Der Worker-Prozess bekommt seine eigene `JobQueue`-Instanz (unverändert), gefüttert
über eine neue IPC-Warteschlange statt direkter Funktionsaufrufe. Die eigentliche Migrationsarbeit
ist schmal: ein Transport-Modul + pro Job eine kleine Anpassung von „Closure direkt an `enqueue()`"
auf „Payload-Dict + Dispatch-Tabelle im Worker" (siehe Kontrakt unten).

**Closures können nicht über die Prozessgrenze.** Heute reicht z.B.
[caption_job.py:277](../../../backend/photofant/jobs/caption_job.py#L277)
`coro_factory=lambda job_status: run_caption_job(job_status, asset_id)` — eine Python-Closure,
die im selben Speicherraum ausgeführt wird. Über eine Prozessgrenze funktioniert das nicht (nicht
picklebar, und selbst wenn: das ausführende Modul muss im Kindprozess ohnehin frisch importiert
sein). Jeder migrierte Job braucht deshalb einen kleinen Umbau: die `enqueue_*`-Funktion schickt
nur noch ein serialisierbares Payload-Dict (z.B. `{"asset_id": 123}`), der Worker-Prozess hat eine
Dispatch-Tabelle `JobKind → Handler-Funktion`, die daraus lokal die Coroutine baut. Mechanisch,
aber an acht Stellen zu wiederholen (Tagging, Captioning, Embedding, Heuristics, Classification,
Face, Clustering, Dupe-Scan) — bei einer Stichprobe (`caption_job.py`) ist der Payload schon heute
nur `asset_id` + zwei einfache Skalare, kein ORM-Objekt. Als Muster erwartet, pro Job zu verifizieren.

**`face_pipeline.py`/`classification_pipeline.py` bleiben im API-Prozess — bewusst.** Beide tracken
nur einen Zähler pro Asset-ID (`dict[int, int]` unter einem `threading.Lock`) und lösen bei
Erreichen von 0 den nächsten Job aus. Sie müssen nicht mit umziehen: der Worker meldet über einen
neuen, zweiten Nachrichtentyp „pipeline_signal" (zusätzlich zu den Job-Status-Updates) ans
API-seitige `face_pipeline.signal()`/`classification_pipeline.signal()` zurück, wenn ein
Prerequisite-Job fertig ist. Löst der Zähler den Folgejob aus, geht der über den ganz normalen
Remote-Enqueue-Pfad wieder zurück in den Worker. Ein Umweg (Worker → API-Signal → API-Enqueue →
Worker), aber für reine Zähler-Logik ohne Performance-Relevanz — und vermeidet, dass Phase 2 und
Phase 3 zwei unterschiedliche Signalisierungs-Mechanismen brauchen (vor/nach der FACE-Migration).
Diese Entscheidung steht schon jetzt fest, damit Phase 2 nicht in eine Sackgasse baut.

**Keine API-Route fasst `session_manager`/`generative_engine`/`gguf_engine` direkt an** (verifiziert:
`grep -rn "session_manager\|generative_engine\|gguf_engine" backend/photofant/api/` — kein Treffer).
Nur Jobs und der Idle-Eviction-Loop in [main.py:57-64](../../../backend/photofant/main.py#L57-L64)
nutzen sie. Beide Nutzergruppen ziehen komplett in den Worker um — es gibt keinen dritten Ort, der
noch Zugriff auf die Modell-Sessions bräuchte.

**Windows nutzt `spawn`, nicht `fork`.** Der Kindprozess importiert alle Module frisch — keine
geerbten CUDA-Kontexte vom API-Prozess (das ist sogar erwünscht: der API-Prozess soll gar keinen
GPU-Kontext aufbauen). Nebenwirkung: `backend/photofant/db/engine.py`s Modul-Level-Singleton
`engine = create_db_engine()` läuft im Worker-Prozess ein zweites Mal — jeder Prozess bekommt seine
eigene Engine-Instanz, das ist gewollt, aber SQLite+WAL-Zugriff aus zwei echten Prozessen (nicht
nur Threads) ist in diesem Projekt bisher unerprobt (siehe Konfidenz-Ausweis).

## Kontrakt (API-Prozess ↔ Worker-Prozess)

Neues Modul `backend/photofant/worker/protocol.py` — reine Datencontainer, keine Closures, keine
ORM-Objekte:

```python
from dataclasses import dataclass
from typing import Any, Literal

@dataclass
class JobRequest:
    """API → Worker: ein Job soll starten. `payload` ist reines JSON (Skalare, Listen, Dicts) —
    niemals ein ORM-Objekt oder eine Closure, die überlebt den Prozesswechsel nicht."""
    job_id: str
    kind: str          # JobKind.value
    label: str
    payload: dict[str, Any]

@dataclass
class JobStatusMessage:
    """Worker → API: Fortschritt/Ergebnis eines Jobs — wird 1:1 in die bestehende
    job_queue._notify()-Pipeline eingespeist, das Frontend merkt vom Umzug nichts."""
    type: Literal["job_status"]
    job_id: str
    progress: float
    state: str          # JobState.value
    error: str | None
    result: dict[str, Any] | None

@dataclass
class PipelineSignalMessage:
    """Worker → API: ein Prerequisite-Job ist fertig — API entscheidet über face_pipeline/
    classification_pipeline, ob der Folgejob jetzt fällig ist (siehe „Wichtige Funde")."""
    type: Literal["pipeline_signal"]
    pipeline: Literal["face", "classification"]
    asset_id: int
```

Dispatch-Tabelle im Worker (`backend/photofant/worker/dispatch.py`, neu) — eine Zeile pro
migriertem `JobKind`, befüllt phasenweise (Phase 2: zwei Zeilen, Phase 3: der Rest):

```python
JOB_HANDLERS: dict[JobKind, Callable[[JobStatus, dict[str, Any]], Coroutine[Any, Any, None]]] = {
    JobKind.CAPTIONING: lambda status, payload: run_caption_job(
        status, payload["asset_id"], payload.get("override_preset_id"), payload.get("force", False)
    ),
    JobKind.TAGGING: lambda status, payload: run_tagging_job(status, payload["asset_id"]),
    # Phase 3 ergänzt: EMBEDDING, HEURISTICS, CLASSIFICATION, FACE, CLUSTERING, DUPE_SCAN
}
```

Transport: `multiprocessing.Queue` (zwei Stück — Request-Richtung, Status-Richtung). Kein
Message-Broker, keine dritte Abhängigkeit — für eine lokale Ein-Nutzer-App ist die
Standardbibliothek genug.

## Finale AK (Gesamt)

- [ ] Lightbox lädt weiterhin flott, während ein Import mit vielen Bildern läuft (Tagging,
      Captioning, Embedding, Heuristics, Classification, Face alle aktiv im Hintergrund).
- [ ] Der Worker-Prozess läuft als eigener Prozess sichtbar neben dem API-Prozess (Task-Manager).
- [ ] Ein hart beendeter Worker-Prozess reißt die API nicht mit — Galerie/Lightbox bleiben
      erreichbar, der unterbrochene Job zeigt `error` statt ewig `running`.
- [ ] Nach einem Worker-Absturz startet ein neuer Worker automatisch, ohne die API neu zu starten.
- [ ] Normaler Shutdown (Server stoppen) hinterlässt keinen verwaisten Kindprozess.
- [ ] Kein API-Route-Handler und keine I/O-Jobklasse (Import, Export, Thumbnail, Backup, Download,
      ComfyUI-Run) fasst nach diesem Plan noch `session_manager`/`generative_engine`/`gguf_engine`
      an — die leben ausschließlich im Worker.
- [ ] ADR-037 dokumentiert die Entscheidung inkl. verworfener Alternativen.

## Risiken

- 🟡 **Windows-`spawn` + große Torch/ONNX-Importe im Kindprozess** — jeder Worker-Start importiert
  torch/onnxruntime neu, das kann spürbar dauern. Falls unangenehm lang: Kandidat für einen
  Warm-Up-Hinweis im Job-Dock statt eines Blockers, kein Show-Stopper.
- 🟡 **SQLite aus zwei echten Prozessen statt nur Threads** — WAL sollte das laut Doku tragen,
  ist in diesem Projekt aber bisher nur Multi-Thread erprobt. Check in Phase 1 (Konfidenz-Ausweis).
- 🟡 **Neuer Signalisierungs-Kanaltyp** (`pipeline_signal`) — noch nirgends im Projekt so gemacht
  (bisher nur Cross-Thread via `run_coroutine_threadsafe`). Muss in Phase 2 am echten Fall
  (Tagging+Captioning → FACE) beweisen, dass FACE zuverlässig genau einmal ausgelöst wird.
- 🟡 **Kein Multi-Worker-Split in v1** — alle migrierten Jobs teilen sich einen Prozess. Wird das
  selbst zum Nadelöhr (z.B. weil Clustering lange CPU-Zeit blockiert, während Captioning wartet),
  ist „mehrere Worker-Prozesse" ein Folge-Plan, kein Teil von diesem.
- 🟡 **Payload-Umbau pro Job** — falls irgendein migrierter Job heute mehr als Skalare durch seinen
  `coro_factory` schleust (ORM-Row, komplexes Objekt statt ID), muss das in der jeweiligen
  Migrations-Phase auf ID-only umgebaut werden. Bei der Stichprobe (`caption_job.py`) ist das
  schon der Fall — als Muster erwartet, pro Job in Phase 2/3 zu verifizieren, nicht blind übernehmen.

## Bewusst draußen (Feature-Radar, max. 1 Punkt — hier verbraucht)

**Mehrere Worker-Prozesse getrennt nach Modelltyp/GPU-Last.** Würde echte Parallelität zwischen
z.B. Tagging und Captioning erlauben statt nur GIL-Fairness gegenüber der API. v1 nimmt einen
einzigen Worker-Prozess — reicht, um das eigentliche Problem (API friert ein) zu lösen, ohne die
zusätzliche Komplexität mehrerer IPC-Kanäle. Backlog-Kandidat, falls der eine Worker-Prozess selbst
zum Nadelöhr wird.

## Konfidenz-Ausweis

1. **Am unsichersten: Cross-Process-Signalisierung für `face_pipeline`/`classification_pipeline`.**
   Neuer Mechanismus, kein Vorbild im Projekt. **Check:** Phase 2, End-to-End mit einem echten
   Bild durch Tagging+Captioning — FACE muss zuverlässig genau einmal ausgelöst werden (nicht 0×,
   nicht 2×), auch wenn Tagging und Captioning in unterschiedlicher Reihenfolge fertig werden.
2. **SQLite aus zwei Prozessen gleichzeitig.** **Check:** Phase 1, sobald der Worker-Prozess steht —
   parallel aus API- und Worker-Prozess lesen/schreiben, auf `database is locked` prüfen.
3. **Windows-`spawn`-Startzeit.** **Check:** Phase 1, Zeit vom Prozess-Spawn bis „Worker ready"-Log
   messen. Bei unangenehmer Dauer: Hinweis im Job-Dock statt Blocker, keine Architektur-Änderung.

## Smoke-Checkliste (du prüfst am Plan-Ende)

1. **Das ursprüngliche Symptom ist weg:** Import mit vielen Bildern anstoßen, währenddessen die
   Lightbox mehrfach öffnen/schließen und durch die Galerie scrollen — keine spürbaren Hänger,
   auch nicht kurz nach dem Start des Imports (wenn die Hintergrund-Queue am vollsten ist).
2. **Prozess-Trennung sichtbar:** Task-Manager zeigt zwei unabhängige Python-Prozesse.
3. **Isolation beweisen:** Worker-Prozess im Task-Manager gezielt beenden, während ein Job läuft —
   API bleibt erreichbar, der Job zeigt danach `error`, ein neuer Worker kommt automatisch hoch,
   der nächste Job läuft normal durch.
4. **Saubere Beendigung:** Server normal stoppen — kein verwaister Kindprozess im Task-Manager.

## Bottom-Sektionen

_(beim Archivieren füllen)_

### Summary
### Files touched
### Commits
### Deviations from plan
### Follow-ups
