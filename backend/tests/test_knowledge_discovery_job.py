"""KnowledgeDiscoveryJob (P38 Phase 3) — Websuche + Gemma schlägt Fakten vor, schreibt
nichts. Modell- und Websuche-Layer werden gemockt (testing.md: „echte Modell-Läufe sind
manuelle Smoke-Tests") — der Parser-Trefferquote-Test gegen echte Personen läuft manuell,
siehe Report-Back dieser Phase."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from photofant.db.models import Base
from photofant.inference.capabilities import GenerationResult
from photofant.inference.web_search import WebSearchError, WebSearchResult
from photofant.jobs.knowledge_discovery_job import (
    _build_queries,
    _build_user_prompt,
    _field_labels_for,
    _merge_results,
    _parse_discovery_output,
    _run_discovery,
)
from photofant.jobs.queue import JobKind, JobStatus
from photofant.knowledge.schema import Attribute, Entity, Owner
from photofant.knowledge.service import EntityNotFoundError, KnowledgeService, PrivateDomainError
from photofant.knowledge.vault import Vault

_ACTOR_ID = "actors/robert-downey-jr"


@pytest.fixture
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'discovery.sqlite'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr("photofant.jobs.knowledge_discovery_job.SessionLocal", factory)
    return factory


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()  # seedet movies.yaml (öffentlich) + private.yaml (privat)
    monkeypatch.setattr("photofant.jobs.knowledge_discovery_job.open_vault", lambda: instance)
    return instance


def _seed_actor(session_factory, vault: Vault, **overrides: object) -> None:
    with session_factory() as session:
        payload: dict[str, object] = {
            "id": _ACTOR_ID,
            "type": "Actor",
            "title": "Robert Downey Jr.",
            "domain": "Movies",
            "owner": Owner.INFERRED,
            "body": "Alter Stub-Text.",
        }
        payload.update(overrides)
        KnowledgeService(session, vault).create_entity(Entity(**payload), payload["owner"])  # type: ignore[arg-type]
        session.commit()


def _seed_private_person(session_factory, vault: Vault) -> None:
    with session_factory() as session:
        entity = Entity(
            id="people/oma-erna", type="Person", title="Oma Erna", domain="Private", owner=Owner.USER
        )
        KnowledgeService(session, vault).create_entity(entity, Owner.USER)
        session.commit()


def _fake_generation(text: str) -> GenerationResult:
    return GenerationResult(
        text=text,
        model_id="gemma-3-12b-obliterated-gguf",
        capability="knowledge_discovery",
        prompt_version="1",
        duration_ms=42.0,
    )


def _job_status() -> JobStatus:
    return JobStatus(id="job-1", kind=JobKind.KNOWLEDGE_DISCOVERY, label="Web-Recherche: test")


_FACT_LINE_1 = "- Feld: taetigkeit | Wert: Schauspieler | Quelle: https://www.imdb.com/name/rdj | Konfidenz: 0.9"
_FACT_LINE_2 = (
    "- Feld: beschreibung | Wert: US-amerikanischer Schauspieler, bekannt für Iron Man. "
    "| Quelle: https://imdb.com/name/rdj | Konfidenz: 0.8"
)
_WELL_FORMED_OUTPUT = f"""### FAKTEN
{_FACT_LINE_1}
{_FACT_LINE_2}

### NEUE_ENTITAETEN
keine

### QUELLEN
https://www.imdb.com/name/rdj
"""


def test_run_discovery_returns_parsed_facts(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_actor(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.search_web",
        lambda query, max_results=5: [
            WebSearchResult(title="RDJ — IMDb", url="https://www.imdb.com/name/rdj", snippet="Actor.")
        ],
    )
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation(_WELL_FORMED_OUTPUT),
    )

    status = _job_status()
    _run_discovery(status, _ACTOR_ID)

    assert status.result is not None
    facts = status.result["facts"]
    assert len(facts) == 2
    assert facts[0] == {
        "field": "taetigkeit",
        "label": "Tätigkeit",
        "value": "Schauspieler",
        "source": "imdb.com",
        "source_url": "https://www.imdb.com/name/rdj",
        "confidence": 0.9,
    }
    # "beschreibung" mappt auf den Body-Sonderfall, nicht auf einen Domänen-Feld-Key.
    assert facts[1]["field"] == "body"
    assert facts[1]["label"] == "Beschreibung"
    assert status.result["entity_suggestions"] == []
    assert status.result["sources"] == ["https://www.imdb.com/name/rdj"]
    assert status.result["errors"] == []
    assert status.result["explainability"]["reason"] == "Web-Recherche — Vorschläge, nichts wurde geschrieben."
    assert status.result["explainability"]["confidence"] is None


def test_run_discovery_does_not_write_the_vault(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_actor(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.search_web", lambda query, max_results=5: []
    )
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation(_WELL_FORMED_OUTPUT),
    )

    _run_discovery(_job_status(), _ACTOR_ID)

    with session_factory() as session:
        entity = KnowledgeService(session, vault).find_entity(_ACTOR_ID)
        assert entity is not None
        assert entity.body == "Alter Stub-Text."  # unverändert — nur ein Vorschlag, kein Write
        assert entity.attributes == {}


def test_run_discovery_missing_entity_raises(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation(_WELL_FORMED_OUTPUT),
    )
    with pytest.raises(EntityNotFoundError):
        _run_discovery(_job_status(), "actors/nobody")


def test_run_discovery_private_domain_raises(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_private_person(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation(_WELL_FORMED_OUTPUT),
    )
    with pytest.raises(PrivateDomainError):
        _run_discovery(_job_status(), "people/oma-erna")


def test_run_discovery_search_error_raises_runtime_error(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_actor(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.search_web",
        lambda query, max_results=5: (_ for _ in ()).throw(WebSearchError("Rate-Limit")),
    )
    with pytest.raises(RuntimeError, match="Rate-Limit"):
        _run_discovery(_job_status(), _ACTOR_ID)


def test_run_discovery_empty_model_output_raises(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_actor(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.search_web", lambda query, max_results=5: []
    )
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation("   "),
    )
    with pytest.raises(RuntimeError):
        _run_discovery(_job_status(), _ACTOR_ID)


def test_run_discovery_broken_output_degrades_to_empty_result(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein Modell-Output ganz ohne Sektions-Marker crasht nicht — leeres Ergebnis,
    der Wizard zeigt „Nichts gefunden" (Docstring-AK Phase 3, Punkt 4)."""
    _seed_actor(session_factory, vault)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.search_web", lambda query, max_results=5: []
    )
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation("Ich bin ein unstrukturierter Fließtext ohne Marker."),
    )

    status = _job_status()
    _run_discovery(status, _ACTOR_ID)

    assert status.result is not None
    assert status.result["facts"] == []
    assert status.result["entity_suggestions"] == []
    assert status.result["errors"] == []


def test_run_discovery_uses_preferred_sources_query(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Actor trägt in movies.yaml `preferred_sources: [imdb.com, wikipedia.org]` — der Job
    muss zuerst eingeschränkt, dann offen suchen und beide Treffer zusammenführen."""
    _seed_actor(session_factory, vault)
    queries: list[str] = []

    def _fake_search(query: str, max_results: int = 5) -> list[WebSearchResult]:
        queries.append(query)
        if "site:" in query:
            return [WebSearchResult(title="RDJ — IMDb", url="https://imdb.com/rdj", snippet="x")]
        return [
            WebSearchResult(title="RDJ — IMDb", url="https://imdb.com/rdj", snippet="x"),
            WebSearchResult(title="RDJ — Sonstwo", url="https://example.test/rdj", snippet="y"),
        ]

    monkeypatch.setattr("photofant.jobs.knowledge_discovery_job.search_web", _fake_search)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation(_WELL_FORMED_OUTPUT),
    )

    _run_discovery(_job_status(), _ACTOR_ID)

    assert len(queries) == 2
    assert "(site:imdb.com OR site:wikipedia.org)" in queries[0]
    assert "site:" not in queries[1]


def test_run_discovery_restricted_search_error_falls_back_to_open(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein zu enger site:-Filter darf die Recherche nicht scheitern lassen (AK Teil A #4)."""
    _seed_actor(session_factory, vault)

    def _fake_search(query: str, max_results: int = 5) -> list[WebSearchResult]:
        if "site:" in query:
            raise WebSearchError("leer/gedrosselt")
        return [WebSearchResult(title="RDJ", url="https://imdb.com/rdj", snippet="x")]

    monkeypatch.setattr("photofant.jobs.knowledge_discovery_job.search_web", _fake_search)
    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.generate",
        lambda *args, **kwargs: _fake_generation(_WELL_FORMED_OUTPUT),
    )

    status = _job_status()
    _run_discovery(status, _ACTOR_ID)

    assert status.result is not None  # kein Absturz, der offene Lauf trägt


def test_run_discovery_open_search_error_still_raises(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scheitert auch der offene Durchlauf, bleibt es beim bisherigen Fehlerverhalten."""
    _seed_actor(session_factory, vault)

    def _fake_search(query: str, max_results: int = 5) -> list[WebSearchResult]:
        raise WebSearchError("Rate-Limit")

    monkeypatch.setattr("photofant.jobs.knowledge_discovery_job.search_web", _fake_search)
    with pytest.raises(RuntimeError, match="Rate-Limit"):
        _run_discovery(_job_status(), _ACTOR_ID)


def test_run_discovery_already_set_attribute_appears_in_prompt(
    session_factory, vault: Vault, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_actor(
        session_factory,
        vault,
        attributes={"taetigkeit": Attribute(value="Schauspieler", owner=Owner.USER)},
    )
    captured: dict[str, str] = {}

    def _capture_generate(capability, prompt, **kwargs):  # type: ignore[no-untyped-def]
        captured["prompt"] = prompt
        return _fake_generation(_WELL_FORMED_OUTPUT)

    monkeypatch.setattr(
        "photofant.jobs.knowledge_discovery_job.search_web", lambda query, max_results=5: []
    )
    monkeypatch.setattr("photofant.jobs.knowledge_discovery_job.generate", _capture_generate)

    _run_discovery(_job_status(), _ACTOR_ID)

    assert "taetigkeit = Schauspieler (von dir gesetzt)" in captured["prompt"]


# --- Query-Bau / Merge-Unit-Tests (keine DB/Modell nötig) ----------------------------


def _actor_entity() -> Entity:
    return Entity(id=_ACTOR_ID, type="Actor", title="Robert Downey Jr.", domain="Movies")


def test_build_queries_without_preferred_returns_single_unchanged_query() -> None:
    queries = _build_queries(_actor_entity(), hint=None, preferred=())
    assert queries == ["Robert Downey Jr. Actor"]


def test_build_queries_with_preferred_returns_restricted_then_open() -> None:
    queries = _build_queries(_actor_entity(), hint=None, preferred=("imdb.com", "wikipedia.org"))
    assert queries == [
        "Robert Downey Jr. Actor (site:imdb.com OR site:wikipedia.org)",
        "Robert Downey Jr. Actor",
    ]


def test_build_queries_appends_hint_to_every_query() -> None:
    queries = _build_queries(_actor_entity(), hint="Marvel", preferred=("imdb.com",))
    assert queries == [
        "Robert Downey Jr. Actor Marvel (site:imdb.com)",
        "Robert Downey Jr. Actor Marvel",
    ]


def test_build_queries_ignores_blank_hint() -> None:
    queries = _build_queries(_actor_entity(), hint="   ", preferred=())
    assert queries == ["Robert Downey Jr. Actor"]


def test_merge_results_dedupes_by_url_preferred_first() -> None:
    primary = [WebSearchResult(title="A", url="https://imdb.com/a", snippet="")]
    fallback = [
        WebSearchResult(title="A dup", url="https://imdb.com/a", snippet=""),
        WebSearchResult(title="B", url="https://example.test/b", snippet=""),
    ]
    merged = _merge_results(primary, fallback, limit=5)
    assert [result.url for result in merged] == ["https://imdb.com/a", "https://example.test/b"]


def test_merge_results_respects_limit() -> None:
    primary = [WebSearchResult(title="A", url=f"https://x.test/{i}", snippet="") for i in range(3)]
    fallback = [WebSearchResult(title="B", url=f"https://y.test/{i}", snippet="") for i in range(3)]
    merged = _merge_results(primary, fallback, limit=4)
    assert len(merged) == 4
    assert [result.url for result in merged] == [
        "https://x.test/0",
        "https://x.test/1",
        "https://x.test/2",
        "https://y.test/0",
    ]


# --- Parser-Unit-Tests (keine DB/Modell nötig) ---------------------------------------


def _labels() -> dict[str, str]:
    return {"taetigkeit": "Tätigkeit", "geburtsort": "Geburtsort", "beschreibung": "Beschreibung"}


def test_parse_discovery_output_drops_unknown_field_and_counts_it() -> None:
    raw = (
        "### FAKTEN\n"
        "- Feld: lieblingsfarbe | Wert: Blau | Quelle: https://x.test | Konfidenz: 0.5\n"
        "- Feld: taetigkeit | Wert: Regisseur | Quelle: https://x.test | Konfidenz: 0.7\n"
        "### NEUE_ENTITAETEN\nkeine\n"
        "### QUELLEN\nhttps://x.test\n"
    )
    output = _parse_discovery_output(raw, _labels())
    assert len(output.facts) == 1
    assert output.facts[0].field == "taetigkeit"
    assert output.errors == ["1 Zeile(n) im Abschnitt FAKTEN konnten nicht gelesen werden"]


def test_parse_discovery_output_missing_confidence_defaults_to_half() -> None:
    raw = (
        "### FAKTEN\n- Feld: taetigkeit | Wert: Regisseur | Quelle: https://x.test\n"
        "### NEUE_ENTITAETEN\nkeine\n### QUELLEN\nkeine\n"
    )
    output = _parse_discovery_output(raw, _labels())
    assert output.facts[0].confidence == 0.5


def test_parse_discovery_output_confidence_clamped_to_unit_range() -> None:
    raw = (
        "### FAKTEN\n- Feld: taetigkeit | Wert: Regisseur | Quelle: https://x.test | Konfidenz: 5\n"
        "### NEUE_ENTITAETEN\nkeine\n### QUELLEN\nkeine\n"
    )
    output = _parse_discovery_output(raw, _labels())
    assert output.facts[0].confidence == 1.0


def test_parse_discovery_output_missing_source_keeps_fact() -> None:
    raw = "### FAKTEN\n- Feld: taetigkeit | Wert: Regisseur\n### NEUE_ENTITAETEN\nkeine\n### QUELLEN\nkeine\n"
    output = _parse_discovery_output(raw, _labels())
    assert len(output.facts) == 1
    assert output.facts[0].source == "—"
    assert output.facts[0].source_url == ""


def test_parse_discovery_output_strips_www_from_source_host() -> None:
    raw = (
        "### FAKTEN\n- Feld: taetigkeit | Wert: Regisseur | Quelle: https://www.imdb.com/x\n"
        "### NEUE_ENTITAETEN\nkeine\n### QUELLEN\nkeine\n"
    )
    output = _parse_discovery_output(raw, _labels())
    assert output.facts[0].source == "imdb.com"


def test_parse_discovery_output_incomplete_new_entity_dropped() -> None:
    raw = (
        "### FAKTEN\nkeine\n"
        "### NEUE_ENTITAETEN\n- Titel: Iron Man | Typ: Movie\n"
        "### QUELLEN\nkeine\n"
    )
    output = _parse_discovery_output(raw, _labels())
    assert output.new_entities == []
    assert output.errors == ["1 Zeile(n) im Abschnitt NEUE_ENTITAETEN konnten nicht gelesen werden"]


def test_parse_discovery_output_completely_unparsable_text_is_empty() -> None:
    output = _parse_discovery_output("Nur Fließtext, keine Marker.", _labels())
    assert output.facts == []
    assert output.new_entities == []
    assert output.sources == []
    assert output.errors == []


def test_parse_discovery_output_sources_filtered_to_http_only() -> None:
    raw = "### FAKTEN\nkeine\n### NEUE_ENTITAETEN\nkeine\n### QUELLEN\nhttps://a.test\nnicht-http\nhttp://b.test\n"
    output = _parse_discovery_output(raw, _labels())
    assert output.sources == ["https://a.test", "http://b.test"]


def test_field_labels_for_always_includes_beschreibung(vault: Vault) -> None:
    domain = vault.load_domain("Movies")
    labels = _field_labels_for(domain, "Actor")
    assert labels["beschreibung"] == "Beschreibung"
    assert labels["taetigkeit"] == "Tätigkeit"


def test_build_user_prompt_lists_allowed_fields_and_results(vault: Vault) -> None:
    domain = vault.load_domain("Movies")
    entity = Entity(id=_ACTOR_ID, type="Actor", title="Robert Downey Jr.", domain="Movies")
    results = [WebSearchResult(title="RDJ", url="https://imdb.com/rdj", snippet="Actor.")]

    prompt = _build_user_prompt(entity, domain, results)

    assert "taetigkeit (Tätigkeit)" in prompt
    assert "[1] RDJ / https://imdb.com/rdj / Actor." in prompt
    assert "Nenne nur Fakten, die durch die Snippets gedeckt sind." in prompt


def test_build_user_prompt_without_results_says_so(vault: Vault) -> None:
    domain = vault.load_domain("Movies")
    entity = Entity(id=_ACTOR_ID, type="Actor", title="Robert Downey Jr.", domain="Movies")

    prompt = _build_user_prompt(entity, domain, [])

    assert "(keine Suchergebnisse)" in prompt
