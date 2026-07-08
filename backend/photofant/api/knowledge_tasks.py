"""Aufgaben-Queue-Endpoint (P23 Phase 1) — CRUD + Statuswechsel auf `knowledge_tasks`.

Getrennt von `api/knowledge.py` (Entity-CRUD, P22): Aufgaben sind Arbeitszustand,
keine Wissensbasis-Mutation, und laufen über einen eigenen Service (`TaskService`)
ohne Vault-Berührung. `POST /lookup` löst den `KnowledgeLookupJob` manuell aus (Scope
laut Plan: automatischer Trigger aus Ereignissen kommt erst in P24).
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.db.models import KnowledgeTask
from photofant.db.session import get_session
from photofant.jobs.knowledge_lookup_job import enqueue_knowledge_lookup
from photofant.jobs.queue import JobStatus
from photofant.knowledge.tasks import (
    InvalidTaskTransitionError,
    TaskKind,
    TaskNotFoundError,
    TaskService,
    TaskStatus,
)

router = APIRouter(prefix="/knowledge")

DbSession = Annotated[Session, Depends(get_session)]

log = logging.getLogger(__name__)


class TaskDto(BaseModel):
    id: int
    kind: str
    status: str
    context: dict[str, Any]
    created_at: str
    resolved_at: str | None

    @classmethod
    def from_task(cls, task: KnowledgeTask) -> TaskDto:
        return cls(
            id=task.id,
            kind=task.kind,
            status=task.status,
            context=dict(task.context),
            created_at=task.created_at.isoformat(),
            resolved_at=task.resolved_at.isoformat() if task.resolved_at else None,
        )


class CreateTaskRequest(BaseModel):
    kind: str
    context: dict[str, Any] = {}


class LookupRequest(BaseModel):
    kind: str
    ref: str


class JobResponse(BaseModel):
    job_id: str


def _parse_kind(value: str) -> TaskKind:
    try:
        return TaskKind(value)
    except ValueError as error:
        allowed = ", ".join(kind.value for kind in TaskKind)
        raise HTTPException(
            status_code=422, detail=f"Unbekannte Aufgaben-Art '{value}' (erlaubt: {allowed})"
        ) from error


def _parse_status(value: str) -> TaskStatus:
    try:
        return TaskStatus(value)
    except ValueError as error:
        allowed = ", ".join(status.value for status in TaskStatus)
        raise HTTPException(
            status_code=422, detail=f"Unbekannter Status '{value}' (erlaubt: {allowed})"
        ) from error


@router.post("/tasks", response_model=TaskDto, status_code=201)
async def create_task(body: CreateTaskRequest, session: DbSession) -> TaskDto:
    service = TaskService(session)
    result = service.create_task(_parse_kind(body.kind), body.context)
    session.commit()
    return TaskDto.from_task(result.task)


@router.get("/tasks", response_model=list[TaskDto])
async def list_tasks(session: DbSession, status: str | None = None) -> list[TaskDto]:
    service = TaskService(session)
    parsed_status = _parse_status(status) if status is not None else None
    return [TaskDto.from_task(task) for task in service.list_tasks(parsed_status)]


@router.post("/tasks/{task_id}/resolve", response_model=TaskDto)
async def resolve_task(task_id: int, session: DbSession) -> TaskDto:
    service = TaskService(session)
    try:
        task = service.resolve_task(task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidTaskTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    session.commit()
    return TaskDto.from_task(task)


@router.post("/tasks/{task_id}/dismiss", response_model=TaskDto)
async def dismiss_task(task_id: int, session: DbSession) -> TaskDto:
    service = TaskService(session)
    try:
        task = service.dismiss_task(task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidTaskTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    session.commit()
    return TaskDto.from_task(task)


@router.post("/lookup", response_model=JobResponse)
async def trigger_lookup(body: LookupRequest) -> JobResponse:
    status: JobStatus = await enqueue_knowledge_lookup(_parse_kind(body.kind), body.ref)
    return JobResponse(job_id=status.id)
