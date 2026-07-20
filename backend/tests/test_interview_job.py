"""InterviewJob — Interview-Antworten → Beschreibungsvorschlag, kein Direkt-Write (P27 Phase 4)."""
from __future__ import annotations

from pathlib import Path

import pytest

from photofant.inference.capabilities import GenerationResult
from photofant.jobs.interview_job import (
    INTERVIEW_CONFIDENCE,
    InterviewAnswer,
    _build_user_prompt,
    _run_interview,
)
from photofant.jobs.queue import JobKind, JobStatus
from photofant.knowledge.schema import MediaLinks
from photofant.knowledge.vault import Vault


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()  # seedet u.a. die mitgelieferte private.yaml
    monkeypatch.setattr("photofant.jobs.interview_job.open_vault", lambda: instance)
    return instance


def _fake_generation(text: str) -> GenerationResult:
    return GenerationResult(
        text=text,
        model_id="gemma-3-4b-it",
        capability="interview",
        prompt_version="2",
        duration_ms=42.0,
    )


def _job_status() -> JobStatus:
    return JobStatus(id="job-1", kind=JobKind.INTERVIEW, label="Interview: Oma Erna")


def _answers() -> list[InterviewAnswer]:
    return [
        InterviewAnswer(question="Wer ist die Person?", answer="Meine Großmutter Erna."),
        InterviewAnswer(question="Beziehung zu dir?", answer="Mütterlicherseits."),
        InterviewAnswer(question="Wichtige Ereignisse?", answer=""),  # übersprungen
    ]


def test_run_interview_returns_suggestion_from_answers(
    vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation("Erna ist die Großmutter mütterlicherseits."),
    )

    status = _job_status()
    _run_interview(status, "Oma Erna", "Private", "Person", MediaLinks(), _answers())

    assert status.result is not None
    suggestion = status.result["suggestion"]
    assert suggestion is not None
    assert suggestion["body"] == "Erna ist die Großmutter mütterlicherseits."
    assert suggestion["domain"] == "Private"
    assert suggestion["type"] == "Person"
    assert status.result["validation_errors"] == []
    explainability = status.result["explainability"]
    assert explainability["confidence"] == INTERVIEW_CONFIDENCE
    assert explainability["capability"] == "interview"
    assert "Web" in explainability["reason"] or "web" in explainability["reason"]


def test_build_user_prompt_only_uses_answered_questions() -> None:
    prompt = _build_user_prompt("Oma Erna", _answers())
    assert "Meine Großmutter Erna." in prompt
    # Die übersprungene (leere) Antwort taucht nicht als Frage-Antwort-Paar auf.
    assert "Wichtige Ereignisse?" not in prompt


def test_run_interview_does_not_write_the_vault(vault: Vault, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation("Ein Absatz."),
    )

    _run_interview(_job_status(), "Oma Erna", "Private", "Person", MediaLinks(), _answers())

    # Der Job ist eine reine Vorschlags-Sackgasse: nichts landet als Datei im Vault.
    assert list(vault.iter_entity_files()) == []


def test_run_interview_empty_model_output_raises(vault: Vault, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation("   "),
    )

    with pytest.raises(RuntimeError):
        _run_interview(_job_status(), "Oma Erna", "Private", "Person", MediaLinks(), _answers())


def test_run_interview_rejected_candidate_carries_no_suggestion_but_keeps_explainability(
    vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation("Ein Absatz."),
    )
    # Validator künstlich scheitern lassen — die Job-Logik reagiert darauf (der Validator
    # selbst hat eigene Tests). Ein abgewiesener Kandidat liefert keinen Vorschlag, behält
    # aber die Explainability für die Anzeige.
    monkeypatch.setattr(
        "photofant.jobs.interview_job.validate_entity",
        lambda entity, domain: ["Feld 'title' fehlt oder ist leer"],
    )

    status = _job_status()
    _run_interview(status, "Oma Erna", "Private", "Person", MediaLinks(), _answers())

    assert status.result is not None
    assert status.result["suggestion"] is None
    assert status.result["validation_errors"] != []
    assert status.result["explainability"]["confidence"] == INTERVIEW_CONFIDENCE
