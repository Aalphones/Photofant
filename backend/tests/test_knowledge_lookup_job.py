"""KnowledgeLookupJob — legt Aufgaben nur für tatsächlich fehlende Entities an (P23 Phase 1)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from photofant.db.models import Base
from photofant.jobs.knowledge_lookup_job import _run_lookup
from photofant.knowledge.schema import Entity, Owner
from photofant.knowledge.service import KnowledgeService
from photofant.knowledge.tasks import TaskKind, TaskService, TaskStatus
from photofant.knowledge.vault import Vault


@pytest.fixture
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'lookup.sqlite'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    # `_run_lookup` öffnet seine eigene Session über `SessionLocal` (Job-Muster,
    # läuft außerhalb des Request-Lebenszyklus) — hier auf die Test-Engine umgebogen.
    monkeypatch.setattr("photofant.jobs.knowledge_lookup_job.SessionLocal", factory)
    return factory


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    monkeypatch.setattr("photofant.jobs.knowledge_lookup_job.open_vault", lambda: instance)
    return instance


def test_run_lookup_creates_task_when_entity_missing(session_factory, vault: Vault) -> None:
    created = _run_lookup(TaskKind.MISSING_ENTITY, "actors/nobody")

    assert created is True
    with session_factory() as session:
        tasks = TaskService(session).list_tasks(TaskStatus.OPEN)
        assert len(tasks) == 1
        assert tasks[0].context == {"ref": "actors/nobody"}


def test_run_lookup_skips_task_when_entity_exists(session_factory, vault: Vault) -> None:
    with session_factory() as session:
        KnowledgeService(session, vault).create_entity(
            Entity(id="actors/robert-downey-jr", type="Actor", title="Robert Downey Jr.", domain="Movies"),
            Owner.USER,
        )
        session.commit()

    created = _run_lookup(TaskKind.MISSING_ENTITY, "actors/robert-downey-jr")

    assert created is False
    with session_factory() as session:
        assert TaskService(session).list_tasks() == []


def test_run_lookup_second_run_same_ref_is_idempotent(session_factory, vault: Vault) -> None:
    first = _run_lookup(TaskKind.MISSING_ENTITY, "actors/nobody")
    second = _run_lookup(TaskKind.MISSING_ENTITY, "actors/nobody")

    assert first is True
    assert second is False
    with session_factory() as session:
        assert len(TaskService(session).list_tasks()) == 1


def test_run_lookup_ambiguous_alias_skips_task(session_factory, vault: Vault) -> None:
    with session_factory() as session:
        service = KnowledgeService(session, vault)
        service.create_entity(
            Entity(
                id="actors/robert-downey-jr",
                type="Actor",
                title="Robert Downey Jr.",
                domain="Movies",
                aliases=["RDJ"],
            ),
            Owner.USER,
        )
        service.create_entity(
            Entity(
                id="actors/robert-de-niro",
                type="Actor",
                title="Robert De Niro",
                domain="Movies",
                aliases=["RDJ"],
            ),
            Owner.USER,
        )
        session.commit()

    created = _run_lookup(TaskKind.MISSING_ENTITY, "RDJ")

    assert created is False
    with session_factory() as session:
        assert TaskService(session).list_tasks() == []
