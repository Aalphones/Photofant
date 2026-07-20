"""KnowledgeUpdateJob — Ergänzungsvorschlag als Patch, kein Direkt-Write (P27 Phase 3)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from photofant.db.models import Base
from photofant.inference.capabilities import GenerationResult
from photofant.jobs.knowledge_update_job import SUGGESTION_CONFIDENCE, _run_update
from photofant.jobs.queue import JobKind, JobStatus
from photofant.knowledge.schema import Entity, Owner
from photofant.knowledge.service import EntityNotFoundError, KnowledgeService
from photofant.knowledge.vault import Vault


@pytest.fixture
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'update.sqlite'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    # `_run_update` öffnet seine eigene Session über `SessionLocal` (Job-Muster) — hier
    # auf die Test-Engine umgebogen.
    monkeypatch.setattr("photofant.jobs.knowledge_update_job.SessionLocal", factory)
    return factory


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    monkeypatch.setattr("photofant.jobs.knowledge_update_job.open_vault", lambda: instance)
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


def _fake_generation(text: str) -> GenerationResult:
    return GenerationResult(
        text=text,
        model_id="gemma-3-4b-it",
        capability="knowledge_update",
        prompt_version="1",
        duration_ms=42.0,
    )


def _job_status() -> JobStatus:
    return JobStatus(id="job-1", kind=JobKind.KNOWLEDGE_UPDATE, label="KI-Ergänzung: test")


def test_run_update_returns_proposal_with_diff_and_explainability(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_entity(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_update_job.generate",
        lambda *args, **kwargs: _fake_generation("Ergänzter, korrigierter Text."),
    )

    status = _job_status()
    _run_update(status, "actors/robert-downey-jr")

    assert status.result is not None
    assert status.result["proposal"] == {"body": "Ergänzter, korrigierter Text."}
    assert status.result["old_body"] == "Alter Stub-Text."
    assert status.result["validation_errors"] == []
    explainability = status.result["explainability"]
    assert explainability["confidence"] == SUGGESTION_CONFIDENCE
    assert explainability["model_id"] == "gemma-3-4b-it"
    assert explainability["prompt_version"] == "1"


def test_run_update_does_not_write_the_vault(session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_entity(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_update_job.generate",
        lambda *args, **kwargs: _fake_generation("Ergänzter Text."),
    )

    _run_update(_job_status(), "actors/robert-downey-jr")

    with session_factory() as session:
        entity = KnowledgeService(session, vault).find_entity("actors/robert-downey-jr")
        assert entity is not None
        assert entity.body == "Alter Stub-Text."  # unverändert — nur ein Vorschlag, kein Write


def test_run_update_missing_entity_raises(session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "photofant.jobs.knowledge_update_job.generate",
        lambda *args, **kwargs: _fake_generation("Text."),
    )

    with pytest.raises(EntityNotFoundError):
        _run_update(_job_status(), "actors/nobody")


def test_run_update_empty_model_output_raises(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_entity(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_update_job.generate",
        lambda *args, **kwargs: _fake_generation("   "),
    )

    with pytest.raises(RuntimeError):
        _run_update(_job_status(), "actors/robert-downey-jr")


def test_run_update_rejected_proposal_carries_no_body_but_keeps_explainability(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_entity(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_update_job.generate",
        lambda *args, **kwargs: _fake_generation("Ergänzter Text."),
    )
    # Validator-Trockenlauf künstlich scheitern lassen — die Job-Logik reagiert darauf,
    # der Validator selbst hat eigene Tests.
    monkeypatch.setattr(
        "photofant.knowledge.service.KnowledgeService.validate_patch",
        lambda self, entity_id, patch: ["Entity-Typ 'Actor' ist in Domäne 'Movies' nicht definiert"],
    )

    status = _job_status()
    _run_update(status, "actors/robert-downey-jr")

    assert status.result is not None
    assert status.result["proposal"] is None
    assert status.result["validation_errors"] != []
    assert status.result["explainability"]["confidence"] == SUGGESTION_CONFIDENCE


def test_run_update_proposal_can_be_generated_for_user_owned_entity(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Die Ownership-Sperre greift erst beim Annehmen (Patch-Pfad, siehe
    # test_knowledge_patch_job.py::test_run_patch_inferred_writer_cannot_downgrade_user_owned_value)
    # — der reine Vorschlag darf für jede Entity erzeugt werden.
    _seed_entity(session_factory, vault, owner=Owner.USER, confidence=1.0)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_update_job.generate",
        lambda *args, **kwargs: _fake_generation("Ergänzter Text."),
    )

    status = _job_status()
    _run_update(status, "actors/robert-downey-jr")

    assert status.result is not None
    assert status.result["proposal"] == {"body": "Ergänzter Text."}
