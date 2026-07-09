"""Scoring-Kern der Empfehlungen (P26 Phase 1) — Graph-Kontext + gewichteter Score.

Der Vektorindex (``vec_asset_embedding``) existiert in der Wegwerf-Test-DB nicht (nur per
Migration angelegt), daher liefert die CLIP-Kandidatensuche hier leer — die Tests prüfen
den **Graph**-Pfad und den Score. Die CLIP+Graph-Kombination selbst wird auf ``score_pair``
mit gesetztem ``clip_similarity`` belegt; das echte Vektor-Zusammenspiel ist manueller Smoke.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from photofant.db.models import (
    Asset,
    AssetInstance,
    KnowledgeEntity,
    KnowledgeMediaLink,
    KnowledgeRelationship,
    Person,
)
from photofant.recommendation.context import build_context
from photofant.recommendation.scoring import (
    SIGNAL_CLIP,
    SIGNAL_SAME_FILM,
    SIGNAL_SAME_PERSON,
    SIGNAL_SAME_ROLE,
    Weights,
    compute_recommendations,
    score_pair,
)

# Default-nahe Gewichte (summieren zu 1.0) — als expliziter Test-Input, unabhängig von settings.json.
_WEIGHTS = Weights(same_person=0.4, same_role=0.25, same_film=0.15, clip_similarity=0.2)


def _settings(**overrides: Any) -> dict[str, Any]:
    recommendations: dict[str, Any] = {
        "enabled": True,
        "max_results": 12,
        "min_score": 0.3,
        "weights": {
            "same_person": 0.4,
            "same_role": 0.25,
            "same_film": 0.15,
            "clip_similarity": 0.2,
        },
    }
    recommendations.update(overrides)
    return {"recommendations": recommendations}


def _add_asset(session: Session, asset_id: int) -> None:
    session.add(Asset(id=asset_id, content_hash=f"hash-{asset_id}"))


def _add_instance(session: Session, asset_id: int, person_id: int) -> None:
    session.add(
        AssetInstance(asset_id=asset_id, person_id=person_id, path=f"/library/{asset_id}-{person_id}.jpg")
    )


def _add_person(session: Session, person_id: int, name: str, is_unknown: bool = False) -> None:
    session.add(Person(id=person_id, name=name, is_unknown=is_unknown))


def _add_entity(session: Session, entity_id: str, title: str, entity_type: str) -> None:
    session.add(
        KnowledgeEntity(
            id=entity_id, type=entity_type, title=title, domain="Movies", owner="user", status=""
        )
    )


def _seed_mcu_graph(session: Session) -> None:
    """Kleiner Movies-Graph: RDJ→Tony Stark→Iron Man→MCU, plus Steve Rogers→Iron Man.

    - Asset 100 (Quelle) + 101: Person RDJ (10), verknüpft mit Tony Stark → teilen Person + Rolle.
    - Asset 102: Person Chris Evans (11) → Steve Rogers, der auch in Iron Man auftaucht → teilt Film.
    - Asset 103: Person (12) → Loki → Thor → kein geteiltes Signal mit der Quelle.
    """
    _add_person(session, 10, "Robert Downey Jr.")
    _add_person(session, 11, "Chris Evans")
    _add_person(session, 12, "Tom Hiddleston")
    for asset_id in (100, 101, 102, 103):
        _add_asset(session, asset_id)
    _add_instance(session, 100, 10)
    _add_instance(session, 101, 10)
    _add_instance(session, 102, 11)
    _add_instance(session, 103, 12)

    _add_entity(session, "characters/tony-stark", "Tony Stark", "Character")
    _add_entity(session, "characters/steve-rogers", "Steve Rogers", "Character")
    _add_entity(session, "characters/loki", "Loki", "Character")
    _add_entity(session, "movies/iron-man", "Iron Man", "Movie")
    _add_entity(session, "movies/thor", "Thor", "Movie")
    _add_entity(session, "franchises/mcu", "MCU", "Franchise")

    session.add_all(
        [
            KnowledgeMediaLink(entity_id="characters/tony-stark", kind="person", target_id=10),
            KnowledgeMediaLink(entity_id="characters/steve-rogers", kind="person", target_id=11),
            KnowledgeMediaLink(entity_id="characters/loki", kind="person", target_id=12),
            KnowledgeRelationship(entity_id="characters/tony-stark", type="appears_in", target="movies/iron-man"),
            KnowledgeRelationship(entity_id="characters/steve-rogers", type="appears_in", target="movies/iron-man"),
            KnowledgeRelationship(entity_id="characters/loki", type="appears_in", target="movies/thor"),
            # part_of ist 2 Hops von der Quell-Rolle entfernt — darf NICHT als "Film" zählen.
            KnowledgeRelationship(entity_id="movies/iron-man", type="part_of", target="franchises/mcu"),
        ]
    )
    session.commit()


def test_build_context_resolves_persons_roles_and_one_hop_films(db_session: Session) -> None:
    _seed_mcu_graph(db_session)

    context = build_context(db_session, 100)

    assert context.persons == {10: "Robert Downey Jr."}
    assert context.roles == {"characters/tony-stark": "Tony Stark"}
    # Film = 1 Hop von der Rolle (appears_in). Das Franchise (2 Hops via part_of) ist NICHT dabei.
    assert context.films == {"movies/iron-man": "Iron Man"}


def test_build_context_excludes_unknown_person(db_session: Session) -> None:
    # Person 1 (_unknown) ist von der conftest-Fixture geseedet.
    _add_asset(db_session, 200)
    _add_instance(db_session, 200, 1)
    db_session.commit()

    context = build_context(db_session, 200)

    assert context.persons == {}


def test_score_pair_combines_clip_and_graph_signals(db_session: Session) -> None:
    _seed_mcu_graph(db_session)
    source = build_context(db_session, 100)
    candidate = build_context(db_session, 101)

    scored = score_pair(101, source, candidate, clip_similarity=0.9, weights=_WEIGHTS)

    # Zwei Fotos derselben Figur im selben Film teilen Person, Rolle UND Film — plus CLIP.
    signals = {reason.signal: reason.detail for reason in scored.reasons}
    assert signals[SIGNAL_SAME_PERSON] == "Robert Downey Jr."
    assert signals[SIGNAL_SAME_ROLE] == "Tony Stark"
    assert signals[SIGNAL_SAME_FILM] == "Iron Man"
    assert signals[SIGNAL_CLIP] == "0.90"
    # 0.4 (Person) + 0.25 (Rolle) + 0.15 (Film) + 0.2*0.9 (CLIP) = 0.98
    assert scored.score == 0.4 + 0.25 + 0.15 + 0.2 * 0.9


def test_score_pair_without_overlap_has_no_reasons(db_session: Session) -> None:
    _seed_mcu_graph(db_session)
    source = build_context(db_session, 100)
    unrelated = build_context(db_session, 103)

    scored = score_pair(103, source, unrelated, clip_similarity=None, weights=_WEIGHTS)

    assert scored.reasons == []
    assert scored.score == 0.0


def test_compute_recommendations_ranks_person_and_role_above_film(db_session: Session) -> None:
    _seed_mcu_graph(db_session)

    # min_score gesenkt, damit der reine Film-Treffer (0.15) sichtbar bleibt und die
    # Rangfolge geprüft werden kann.
    results = compute_recommendations(db_session, 100, _settings(min_score=0.1))

    by_id = {result.asset_id: result for result in results}
    assert set(by_id) == {101, 102}  # 103 (kein Signal) fällt raus
    # 101 (Person+Rolle+Film = 0.8) rankt vor 102 (nur Film = 0.15).
    assert [result.asset_id for result in results] == [101, 102]
    assert {reason.signal for reason in by_id[101].reasons} == {
        SIGNAL_SAME_PERSON, SIGNAL_SAME_ROLE, SIGNAL_SAME_FILM,
    }
    assert {reason.signal for reason in by_id[102].reasons} == {SIGNAL_SAME_FILM}
    assert by_id[101].score == 0.8


def test_compute_recommendations_applies_min_score_threshold(db_session: Session) -> None:
    _seed_mcu_graph(db_session)

    # Default-Schwelle 0.3: der reine Film-Treffer (102, 0.15) fällt weg, Person+Rolle (101) bleibt.
    results = compute_recommendations(db_session, 100, _settings())

    assert [result.asset_id for result in results] == [101]


def test_compute_recommendations_empty_when_disabled(db_session: Session) -> None:
    _seed_mcu_graph(db_session)

    assert compute_recommendations(db_session, 100, _settings(enabled=False)) == []
