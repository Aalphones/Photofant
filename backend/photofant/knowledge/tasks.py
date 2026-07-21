"""TaskService — Aufgaben-Queue für „hier fehlt Wissen" (P23 Phase 1).

Reiner Arbeitszustand über der Wissensbasis (``knowledge_tasks``), kein Vault-Wissen —
Gegenstück zu ``KnowledgeService`` (die Entity-Mutationsschicht). Dedup passiert über
``kind`` + ``context``-Gleichheit unter offenen Aufgaben: ``KnowledgeLookupJob`` (und
später P24s Event-Trigger) rufen ``create_task`` wiederholt für denselben fehlenden
Verweis auf, ohne die Queue mit Duplikaten zu fluten.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import KnowledgeTask


class TaskKind(StrEnum):
    NEW_PERSON = "new_person"
    MISSING_ENTITY = "missing_entity"
    CONFIRM_RELATIONSHIP = "confirm_relationship"
    REVIEW_RECOMMENDATION = "review_recommendation"
    INCOMPLETE_ENTITY = "incomplete_entity"
    # P38 Phase 4 — Merkmale + Namens-Abgleich.
    MISSING_FIELD = "missing_field"
    LOW_COMPLETENESS = "low_completeness"
    AUTO_LINK = "auto_link"


class TaskStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class TaskNotFoundError(LookupError):
    """``task_id`` ist unbekannt."""


class InvalidTaskTransitionError(ValueError):
    """Statuswechsel ist nur aus ``open`` heraus erlaubt — eine Aufgabe schließt genau einmal."""


@dataclass(frozen=True)
class TaskCreationResult:
    """Rückgabe von ``create_task`` — ``created`` unterscheidet Neuanlage von Dedup-Treffer."""

    task: KnowledgeTask
    created: bool


class TaskService:
    """Einzige Mutationsschicht der Aufgaben-Queue."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_task(self, kind: TaskKind, context: dict[str, Any]) -> TaskCreationResult:
        """Legt eine offene Aufgabe an — idempotent über ``kind`` + ``context``.

        Existiert bereits eine **offene** Aufgabe mit gleichem ``kind`` und exakt
        gleichem ``context``, wird sie unverändert zurückgegeben (``created=False``)
        statt ein Duplikat anzulegen. Bereits erledigte/verworfene Aufgaben blockieren
        eine neue Anlage nicht — ein erneut auftretender Lookup nach dem Abarbeiten
        ist ein legitimer neuer Fall.
        """
        existing = self._find_open_duplicate(kind, context)
        if existing is not None:
            return TaskCreationResult(task=existing, created=False)

        task = KnowledgeTask(
            kind=kind.value,
            status=TaskStatus.OPEN.value,
            context=dict(context),
            created_at=datetime.now(UTC),
        )
        self.session.add(task)
        self.session.flush()
        return TaskCreationResult(task=task, created=True)

    def list_tasks(self, status: TaskStatus | None = None) -> list[KnowledgeTask]:
        statement = select(KnowledgeTask).order_by(KnowledgeTask.created_at.desc())
        if status is not None:
            statement = statement.where(KnowledgeTask.status == status.value)
        return list(self.session.execute(statement).scalars())

    def resolve_task(self, task_id: int) -> KnowledgeTask:
        return self._close(task_id, TaskStatus.RESOLVED)

    def dismiss_task(self, task_id: int) -> KnowledgeTask:
        return self._close(task_id, TaskStatus.DISMISSED)

    def _close(self, task_id: int, target: TaskStatus) -> KnowledgeTask:
        task = self._require_task(task_id)
        if task.status != TaskStatus.OPEN.value:
            raise InvalidTaskTransitionError(
                f"Aufgabe '{task_id}' ist bereits '{task.status}', kein Wechsel nach '{target.value}'"
            )
        task.status = target.value
        task.resolved_at = datetime.now(UTC)
        return task

    def _require_task(self, task_id: int) -> KnowledgeTask:
        task = self.session.get(KnowledgeTask, task_id)
        if task is None:
            raise TaskNotFoundError(f"Aufgabe '{task_id}' nicht gefunden")
        return task

    def _find_open_duplicate(self, kind: TaskKind, context: dict[str, Any]) -> KnowledgeTask | None:
        open_tasks = self.session.execute(
            select(KnowledgeTask).where(
                KnowledgeTask.kind == kind.value, KnowledgeTask.status == TaskStatus.OPEN.value
            )
        ).scalars()
        for candidate in open_tasks:
            if candidate.context == context:
                return candidate
        return None
