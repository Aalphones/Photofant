"""Domänen-Parser: neue Schlüssel `question` und `preferred_sources` (P39 Phase 1).

Deckt Rückwärtskompatibilität (Domäne ohne die neuen Schlüssel lädt unverändert),
die Auflösungsregel für bevorzugte Quellen (Typ schlägt Domäne) und die
Fehlerfälle bei ungültigen Werten ab.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from photofant.knowledge.domains import DomainLoadError, load_domain


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "domain.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_domain_without_new_keys_loads_unchanged(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        name: Legacy
        entity_types:
          - name: Thing
            folder: things
            fields:
              - key: color
                label: Color
        """,
    )

    domain = load_domain(path)

    assert domain.preferred_sources == ()
    field = domain.fields_for("Thing")[0]
    assert field.question is None
    assert domain.questions_for("Thing") == ()
    assert domain.preferred_sources_for("Thing") == ()


def test_questions_for_filters_and_preserves_yaml_order(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        name: Private
        entity_types:
          - name: Person
            folder: people
            fields:
              - key: geburtstag
                label: Geburtstag
                question: Wann hat {name} Geburtstag?
              - key: beruf
                label: Beruf
              - key: wohnort
                label: Wohnort
                question: Wo wohnt {name}?
        """,
    )

    domain = load_domain(path)

    questions = domain.questions_for("Person")
    assert [field.key for field in questions] == ["geburtstag", "wohnort"]
    assert questions[0].question == "Wann hat {name} Geburtstag?"


def test_preferred_sources_type_overrides_domain(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        name: Movies
        preferred_sources:
          - wikipedia.org
        entity_types:
          - name: Actor
            folder: actors
            preferred_sources:
              - IMDb.com
              - WWW.Wikipedia.org
          - name: Series
            folder: series
        """,
    )

    domain = load_domain(path)

    assert domain.preferred_sources_for("Actor") == ("imdb.com", "wikipedia.org")
    assert domain.preferred_sources_for("Series") == ("wikipedia.org",)


def test_preferred_sources_normalizes_www_and_case(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        name: Movies
        preferred_sources:
          - WWW.IMDb.COM
        entity_types:
          - name: Movie
            folder: movies
        """,
    )

    domain = load_domain(path)

    assert domain.preferred_sources == ("imdb.com",)


def test_invalid_question_raises_domain_load_error(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        name: Broken
        entity_types:
          - name: Thing
            folder: things
            fields:
              - key: color
                label: Color
                question: [not, a, string]
        """,
    )

    with pytest.raises(DomainLoadError):
        load_domain(path)


def test_invalid_preferred_sources_raises_domain_load_error(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        name: Broken
        preferred_sources: not-a-list
        entity_types:
          - name: Thing
            folder: things
        """,
    )

    with pytest.raises(DomainLoadError):
        load_domain(path)


def test_invalid_preferred_sources_entry_raises_domain_load_error(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        name: Broken
        preferred_sources:
          - 42
        entity_types:
          - name: Thing
            folder: things
        """,
    )

    with pytest.raises(DomainLoadError):
        load_domain(path)
