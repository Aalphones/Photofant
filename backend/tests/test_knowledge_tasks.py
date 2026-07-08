"""TaskService — Dedup über kind+context, Statuswechsel-Regeln (P23 Phase 1)."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from photofant.knowledge.tasks import (
    InvalidTaskTransitionError,
    TaskKind,
    TaskNotFoundError,
    TaskService,
    TaskStatus,
)


@pytest.fixture
def service(db_session: Session) -> TaskService:
    return TaskService(db_session)


def test_create_task_persists_open_task(service: TaskService) -> None:
    result = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "actors/robert-downey-jr"})

    assert result.created is True
    assert result.task.status == TaskStatus.OPEN.value
    assert result.task.context == {"ref": "actors/robert-downey-jr"}
    assert result.task.resolved_at is None


def test_create_task_dedups_same_kind_and_context(service: TaskService) -> None:
    first = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "actors/robert-downey-jr"})
    second = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "actors/robert-downey-jr"})

    assert second.created is False
    assert second.task.id == first.task.id


def test_create_task_does_not_dedup_different_context(service: TaskService) -> None:
    first = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "actors/robert-downey-jr"})
    second = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "actors/robert-de-niro"})

    assert second.created is True
    assert second.task.id != first.task.id


def test_create_task_does_not_dedup_different_kind(service: TaskService) -> None:
    context = {"ref": "actors/robert-downey-jr"}
    first = service.create_task(TaskKind.MISSING_ENTITY, context)
    second = service.create_task(TaskKind.NEW_PERSON, context)

    assert second.created is True
    assert second.task.id != first.task.id


def test_create_task_allows_new_task_after_previous_resolved(service: TaskService) -> None:
    context = {"ref": "actors/robert-downey-jr"}
    first = service.create_task(TaskKind.MISSING_ENTITY, context)
    service.resolve_task(first.task.id)

    second = service.create_task(TaskKind.MISSING_ENTITY, context)

    assert second.created is True
    assert second.task.id != first.task.id


def test_list_tasks_filters_by_status(service: TaskService) -> None:
    open_task = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "a"}).task
    resolved_task = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "b"}).task
    service.resolve_task(resolved_task.id)

    open_only = service.list_tasks(TaskStatus.OPEN)
    resolved_only = service.list_tasks(TaskStatus.RESOLVED)

    assert [task.id for task in open_only] == [open_task.id]
    assert [task.id for task in resolved_only] == [resolved_task.id]


def test_list_tasks_without_filter_returns_all(service: TaskService) -> None:
    service.create_task(TaskKind.MISSING_ENTITY, {"ref": "a"})
    service.create_task(TaskKind.MISSING_ENTITY, {"ref": "b"})

    assert len(service.list_tasks()) == 2


def test_resolve_task_sets_status_and_timestamp(service: TaskService) -> None:
    task = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "a"}).task

    resolved = service.resolve_task(task.id)

    assert resolved.status == TaskStatus.RESOLVED.value
    assert resolved.resolved_at is not None


def test_dismiss_task_sets_status_and_timestamp(service: TaskService) -> None:
    task = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "a"}).task

    dismissed = service.dismiss_task(task.id)

    assert dismissed.status == TaskStatus.DISMISSED.value
    assert dismissed.resolved_at is not None


def test_resolve_task_missing_raises_not_found(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.resolve_task(999)


def test_resolve_task_twice_raises_invalid_transition(service: TaskService) -> None:
    task = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "a"}).task
    service.resolve_task(task.id)

    with pytest.raises(InvalidTaskTransitionError):
        service.resolve_task(task.id)


def test_dismiss_resolved_task_raises_invalid_transition(service: TaskService) -> None:
    task = service.create_task(TaskKind.MISSING_ENTITY, {"ref": "a"}).task
    service.resolve_task(task.id)

    with pytest.raises(InvalidTaskTransitionError):
        service.dismiss_task(task.id)
