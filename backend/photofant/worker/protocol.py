"""IPC-Kontrakt zwischen API-Prozess und Worker-Prozess (ADR-037).

Reine Datencontainer, keine Closures, keine ORM-Objekte — alles hier muss über eine
`multiprocessing.Queue` picklebar sein und den Prozesswechsel überleben.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class JobRequest:
    """API → Worker: ein Job soll starten.

    `payload` ist reines JSON (Skalare, Listen, Dicts) — niemals ein ORM-Objekt oder eine
    Closure, die den Prozesswechsel nicht überlebt.
    """

    job_id: str
    kind: str  # JobKind.value
    label: str
    payload: dict[str, Any]


@dataclass
class JobStatusMessage:
    """Worker → API: Fortschritt/Ergebnis eines Jobs.

    Wird 1:1 in die bestehende `JobQueue._notify()`-Pipeline eingespeist — das Frontend
    merkt vom Umzug in den Worker-Prozess nichts.
    """

    type: Literal["job_status"]
    job_id: str
    progress: float
    state: str  # JobState.value
    error: str | None
    result: dict[str, Any] | None


@dataclass
class PipelineSignalMessage:
    """Worker → API: ein Prerequisite-Job ist fertig.

    Die API entscheidet über `face_pipeline`/`classification_pipeline`, ob der Folgejob
    jetzt fällig ist (siehe Plan-README „Wichtige Funde"). Ab Phase 2 verdrahtet.
    """

    type: Literal["pipeline_signal"]
    pipeline: Literal["face", "classification"]
    asset_id: int


WorkerStatusMessage = JobStatusMessage | PipelineSignalMessage
