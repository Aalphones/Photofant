"""KnowledgePatchJob (P25 Phase 3) — „Das stimmt nicht" → Korrektur als Patch.

Wendet einen Einzelfeld-Patch über den P22-Ownership-Pfad an (``KnowledgeService.
update_entity``) und protokolliert die Änderung als Explainability-Eintrag
(``ChangelogService``). Läuft als eigener Job statt synchron im REST-Handler, weil
jede Wissensbasis-Mutation laut Architektur (Dok 030) über die Job Queue läuft —
sichtbar im Job-Dock, mit eigener Job-Id für den Explainability-Log.

Reine Sackgasse wie ``KnowledgeLookupJob`` (P23): löst keine Folge-Jobs aus. Der
``owner``-Parameter bleibt bewusst offen (nicht hart auf ``user`` verdrahtet) —
P27s ``KnowledgeUpdateJob`` („Ergänzen (KI)" annehmen) ruft denselben Patch-Pfad
mit einem anderen Owner auf, siehe P27-Phase-3-README: „Annehmen schreibt über
den P25-Patch-Pfad".
"""
from __future__ import annotations

import asyncio
import dataclasses
import logging
from typing import Any

from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.knowledge.changelog import ChangelogService
from photofant.knowledge.schema import Owner
from photofant.knowledge.service import EntityNotFoundError, KnowledgeService
from photofant.knowledge.vault import open_vault

log = logging.getLogger(__name__)


def _jsonable(value: Any) -> Any:
    """Macht Dataclass-Feldwerte (``MediaLinks``, ``list[Relationship]``) JSON-fähig für
    die ``knowledge_changelog``-Spalte — Skalare/Listen von Skalaren bleiben unverändert."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _run_patch(
    job_id: str, entity_id: str, field: str, value: Any, reason: str, owner: Owner
) -> None:
    vault = open_vault()
    with SessionLocal() as session:
        service = KnowledgeService(session, vault)
        entity = service.find_entity(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity '{entity_id}' nicht gefunden")
        old_value = _jsonable(getattr(entity, field))

        service.update_entity(entity_id, {field: value}, owner)

        ChangelogService(session).record(
            entity_id=entity_id,
            field=field,
            old_value=old_value,
            new_value=_jsonable(value),
            reason=reason,
            source=owner.value,
            job_id=job_id,
        )
        session.commit()
        log.info("knowledge_patch: '%s'.%s korrigiert (Job %s)", entity_id, field, job_id)


async def run_knowledge_patch_job(
    status: JobStatus, entity_id: str, field: str, value: Any, reason: str, owner: Owner
) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_patch, status.id, entity_id, field, value, reason, owner)


async def enqueue_knowledge_patch(
    entity_id: str, field: str, value: Any, reason: str, owner: Owner
) -> JobStatus:
    async def _factory(status: JobStatus) -> None:
        await run_knowledge_patch_job(status, entity_id, field, value, reason, owner)

    return await job_queue.enqueue(
        kind=JobKind.KNOWLEDGE_PATCH,
        label=f"Wissens-Korrektur: {entity_id}.{field}",
        coro_factory=_factory,
    )
