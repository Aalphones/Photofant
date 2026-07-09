"""KnowledgePatchJob — Einzelfeld-Korrektur + Explainability-Eintrag (P25 Phase 3)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from photofant.db.models import Base
from photofant.jobs.knowledge_patch_job import _run_patch
from photofant.knowledge.changelog import ChangelogService
from photofant.knowledge.schema import Entity, Owner, Relationship
from photofant.knowledge.service import EntityNotFoundError, KnowledgeService, OwnershipConflictError
from photofant.knowledge.vault import Vault


@pytest.fixture
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'patch.sqlite'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    # `_run_patch` öffnet seine eigene Session über `SessionLocal` (Job-Muster, läuft
    # außerhalb des Request-Lebenszyklus) — hier auf die Test-Engine umgebogen.
    monkeypatch.setattr("photofant.jobs.knowledge_patch_job.SessionLocal", factory)
    return factory


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    monkeypatch.setattr("photofant.jobs.knowledge_patch_job.open_vault", lambda: instance)
    return instance


def _seed_entity(session_factory, vault: Vault, **overrides: object) -> None:
    with session_factory() as session:
        payload: dict[str, object] = {
            "id": "actors/robert-downey-jr",
            "type": "Actor",
            "title": "Robert Downey Jr.",
            "domain": "Movies",
            "owner": Owner.INFERRED,
            "confidence": 0.6,
            "body": "Alter Stub-Text.",
        }
        payload.update(overrides)
        KnowledgeService(session, vault).create_entity(Entity(**payload), payload["owner"])  # type: ignore[arg-type]
        session.commit()


def test_run_patch_updates_field_and_bumps_owner_to_user(session_factory, vault: Vault) -> None:
    _seed_entity(session_factory, vault)

    _run_patch("job-1", "actors/robert-downey-jr", "body", "Korrigierter Text.", "Grund X", Owner.USER)

    with session_factory() as session:
        entity = KnowledgeService(session, vault).find_entity("actors/robert-downey-jr")
        assert entity is not None
        assert entity.body == "Korrigierter Text."
        assert entity.owner is Owner.USER
        assert entity.confidence == 1.0  # USER erzwingt confidence=1.0 (Kontrakt)


def test_run_patch_writes_changelog_entry_with_old_and_new_value(session_factory, vault: Vault) -> None:
    _seed_entity(session_factory, vault)

    _run_patch("job-2", "actors/robert-downey-jr", "body", "Korrigierter Text.", "Grund X", Owner.USER)

    with session_factory() as session:
        entries = ChangelogService(session).list_for_entity("actors/robert-downey-jr")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.field == "body"
        assert entry.old_value == "Alter Stub-Text."
        assert entry.new_value == "Korrigierter Text."
        assert entry.reason == "Grund X"
        assert entry.source == "user"
        assert entry.job_id == "job-2"


def test_run_patch_serializes_dataclass_field_values_for_changelog(session_factory, vault: Vault) -> None:
    _seed_entity(session_factory, vault, relationships=[Relationship(type="appears_in", target="actors/x")])

    _run_patch(
        "job-3",
        "actors/robert-downey-jr",
        "relationships",
        [{"type": "appears_in", "target": "actors/y"}],
        "Falsche Person",
        Owner.USER,
    )

    with session_factory() as session:
        entry = ChangelogService(session).list_for_entity("actors/robert-downey-jr")[0]
        assert entry.old_value == [{"type": "appears_in", "target": "actors/x"}]
        assert entry.new_value == [{"type": "appears_in", "target": "actors/y"}]


def test_run_patch_missing_entity_raises_and_writes_no_changelog(session_factory, vault: Vault) -> None:
    with pytest.raises(EntityNotFoundError):
        _run_patch("job-4", "actors/nobody", "body", "x", "y", Owner.USER)

    with session_factory() as session:
        assert ChangelogService(session).list_for_entity("actors/nobody") == []


def test_run_patch_inferred_writer_cannot_downgrade_user_owned_value(session_factory, vault: Vault) -> None:
    _seed_entity(session_factory, vault, owner=Owner.USER, confidence=1.0)

    with pytest.raises(OwnershipConflictError):
        _run_patch("job-5", "actors/robert-downey-jr", "body", "x", "y", Owner.INFERRED)
