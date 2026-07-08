"""KnowledgeLookupJob (P23 Phase 1) — legt eine Aufgabe an, wenn eine Entity fehlt.

Reiner Nachweis-Job ohne KI (die kommt erst mit P27): prüft per
`KnowledgeService.find_entity`, ob `ref` (Entity-`id` oder Alias) im Vault existiert,
und legt sonst eine `knowledge_tasks`-Zeile an. Dedup läuft über `TaskService.create_task`
(gleicher `kind` + `context` → kein zweiter Eintrag). Automatischer Trigger aus
Ereignissen kommt erst in P24 — hier ist der Job nur manuell auslösbar
(`POST /api/knowledge/lookup`, siehe `api/knowledge_tasks.py`).
"""
from __future__ import annotations

import asyncio
import logging

from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.knowledge.service import AmbiguousEntityError, KnowledgeService
from photofant.knowledge.tasks import TaskKind, TaskService
from photofant.knowledge.vault import open_vault

log = logging.getLogger(__name__)


def _run_lookup(kind: TaskKind, ref: str) -> bool:
    """Legt bei fehlender Entity eine Aufgabe an. Gibt zurück, ob eine neu angelegt wurde.

    Ein mehrdeutiger Alias (`AmbiguousEntityError`) zählt als „gefunden" — die Entity
    existiert ja, nur nicht eindeutig; das ist kein Fall für „hier fehlt Wissen".
    """
    context = {"ref": ref}
    vault = open_vault()
    with SessionLocal() as session:
        service = KnowledgeService(session, vault)
        try:
            entity = service.find_entity(ref)
        except AmbiguousEntityError:
            log.info("knowledge_lookup: '%s' ist mehrdeutig, keine Aufgabe", ref)
            return False
        if entity is not None:
            return False

        result = TaskService(session).create_task(kind, context)
        session.commit()
        if result.created:
            log.info("knowledge_lookup: Aufgabe #%d für '%s' angelegt", result.task.id, ref)
        return result.created


async def run_knowledge_lookup_job(status: JobStatus, kind: TaskKind, ref: str) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_lookup, kind, ref)


async def enqueue_knowledge_lookup(kind: TaskKind, ref: str) -> JobStatus:
    async def _factory(status: JobStatus) -> None:
        await run_knowledge_lookup_job(status, kind, ref)

    return await job_queue.enqueue(
        kind=JobKind.KNOWLEDGE_LOOKUP,
        label=f"Wissens-Lookup: {ref}",
        coro_factory=_factory,
    )
