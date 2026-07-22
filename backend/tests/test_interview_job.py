"""InterviewJob — Interview-Antworten → Beschreibungsvorschlag, kein Direkt-Write (P27 Phase 4)."""
from __future__ import annotations

from pathlib import Path

import pytest

from photofant.inference.capabilities import GenerationResult
from photofant.jobs.interview_job import (
    INFERRED_FALLBACK_CONFIDENCE,
    INTERVIEW_CONFIDENCE,
    InterviewAnswer,
    _build_user_prompt,
    _parse_interview_output,
    _run_interview,
)
from photofant.jobs.queue import JobKind, JobStatus
from photofant.knowledge.domains import FieldDef
from photofant.knowledge.schema import MediaLinks, Owner
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
    prompt = _build_user_prompt("Oma Erna", _answers(), ())
    assert "Meine Großmutter Erna." in prompt
    # Die übersprungene (leere) Antwort taucht nicht als Frage-Antwort-Paar auf.
    assert "Wichtige Ereignisse?" not in prompt
    # Ohne offene Merkmale bleibt der Merkmals-Block ganz weg.
    assert "Noch offene Merkmale" not in prompt


def test_build_user_prompt_lists_open_fields_with_labels() -> None:
    open_fields = (FieldDef(key="beruf", label="Beruf", question="Was macht {name} beruflich?"),)
    prompt = _build_user_prompt("Oma Erna", _answers(), open_fields)
    assert "Noch offene Merkmale" in prompt
    assert "- beruf (Beruf)" in prompt


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


# --- P39 Phase 2: gefragte Merkmale + optionale Modell-Schätzung -------------------------


_ALLOWED = {"geburtstag", "beruf", "wohnort"}


def test_parse_output_reads_body_and_attributes() -> None:
    raw = '{"body": "Ein Absatz.", "attributes": {"beruf": {"value": "Lehrerin", "confidence": 0.8}}}'

    body, attributes = _parse_interview_output(raw, _ALLOWED)

    assert body == "Ein Absatz."
    assert attributes["beruf"].value == "Lehrerin"
    assert attributes["beruf"].owner is Owner.INFERRED
    assert attributes["beruf"].confidence == 0.8


def test_parse_output_strips_code_fence() -> None:
    raw = '```json\n{"body": "Ein Absatz.", "attributes": {}}\n```'

    body, attributes = _parse_interview_output(raw, _ALLOWED)

    assert body == "Ein Absatz."
    assert attributes == {}


def test_parse_output_falls_back_to_plain_text_on_broken_json() -> None:
    raw = "  Erna ist die Großmutter mütterlicherseits.  "

    body, attributes = _parse_interview_output(raw, _ALLOWED)

    assert body == "Erna ist die Großmutter mütterlicherseits."
    assert attributes == {}


def test_parse_output_drops_unknown_keys_and_empty_values() -> None:
    raw = (
        '{"body": "Ein Absatz.", "attributes": {'
        '"lieblingsfarbe": {"value": "Blau"},'  # nicht in der Domäne
        '"wohnort": {"value": "   "},'  # leerer Wert
        '"beruf": {"value": "Lehrerin"}}}'
    )

    _, attributes = _parse_interview_output(raw, _ALLOWED)

    assert set(attributes) == {"beruf"}


def test_parse_output_clamps_confidence() -> None:
    raw = (
        '{"body": "Ein Absatz.", "attributes": {'
        '"beruf": {"value": "Lehrerin", "confidence": 7},'
        '"wohnort": {"value": "Kiel", "confidence": "hoch"},'
        '"geburtstag": {"value": "3. Mai", "confidence": -2}}}'
    )

    _, attributes = _parse_interview_output(raw, _ALLOWED)

    assert attributes["beruf"].confidence == 1.0
    assert attributes["wohnort"].confidence == INFERRED_FALLBACK_CONFIDENCE
    assert attributes["geburtstag"].confidence == 0.0


def test_answered_field_is_taken_verbatim_and_owned_by_user(
    vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation('{"body": "Ein Absatz.", "attributes": {}}'),
    )
    answers = [
        InterviewAnswer(question="Was schätzt du an Erna?", answer="Ihre Ruhe."),
        InterviewAnswer(question="Was macht Erna beruflich?", answer=" Lehrerin ", field_key="beruf"),
    ]

    status = _job_status()
    _run_interview(status, "Oma Erna", "Private", "Person", MediaLinks(), answers)

    assert status.result is not None
    attributes = status.result["suggestion"]["attributes"]
    assert attributes["beruf"]["value"] == "Lehrerin"
    assert attributes["beruf"]["owner"] == Owner.USER.value
    assert attributes["beruf"]["confidence"] == INTERVIEW_CONFIDENCE
    assert attributes["beruf"]["label"] == "Beruf"


def test_answered_field_beats_model_suggestion_for_same_key(
    vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Das Modell schlägt denselben Key vor, den der Nutzer schon beantwortet hat (AK 6).
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation(
            '{"body": "Ein Absatz.", "attributes": {"beruf": {"value": "Bäckerin", "confidence": 0.9}}}'
        ),
    )
    answers = [InterviewAnswer(question="Beruf?", answer="Lehrerin", field_key="beruf")]

    status = _job_status()
    _run_interview(status, "Oma Erna", "Private", "Person", MediaLinks(), answers)

    assert status.result is not None
    beruf = status.result["suggestion"]["attributes"]["beruf"]
    assert beruf["value"] == "Lehrerin"
    assert beruf["owner"] == Owner.USER.value


def test_unknown_field_key_is_dropped(vault: Vault, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation('{"body": "Ein Absatz.", "attributes": {}}'),
    )
    answers = [InterviewAnswer(question="Lieblingsfarbe?", answer="Blau", field_key="lieblingsfarbe")]

    status = _job_status()
    _run_interview(status, "Oma Erna", "Private", "Person", MediaLinks(), answers)

    assert status.result is not None
    assert status.result["suggestion"]["attributes"] == {}


def test_answered_fields_survive_broken_model_json(
    vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    # AK 7: kaputtes JSON darf das Interview nicht scheitern lassen — der Text wird zum
    # Absatz, die gefragten Merkmale hängen nicht am Modell.
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation("Erna ist Lehrerin und wohnt in Kiel."),
    )
    answers = [
        InterviewAnswer(question="Beruf?", answer="Lehrerin", field_key="beruf"),
        InterviewAnswer(question="Wohnort?", answer="Kiel", field_key="wohnort"),
    ]

    status = _job_status()
    _run_interview(status, "Oma Erna", "Private", "Person", MediaLinks(), answers)

    assert status.result is not None
    suggestion = status.result["suggestion"]
    assert suggestion["body"] == "Erna ist Lehrerin und wohnt in Kiel."
    assert set(suggestion["attributes"]) == {"beruf", "wohnort"}


def test_interview_without_any_answers_yields_result_without_attributes(
    vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "photofant.jobs.interview_job.generate",
        lambda *args, **kwargs: _fake_generation('{"body": "Wenig bekannt.", "attributes": {}}'),
    )

    status = _job_status()
    _run_interview(status, "Oma Erna", "Private", "Person", MediaLinks(), [])

    assert status.result is not None
    assert status.result["validation_errors"] == []
    assert status.result["suggestion"]["attributes"] == {}
