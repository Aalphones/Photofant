from __future__ import annotations

from sqlalchemy.orm import Session

from photofant.db.models import (
    KnowledgeEntity,
    KnowledgeMediaLink,
    KnowledgeRelationship,
    KnowledgeSource,
)
from photofant.knowledge.repository import EntityRepository, RelationshipRepository
from photofant.knowledge.schema import Entity, MediaLinks, Owner, Relationship


def _rdj(**overrides: object) -> Entity:
    defaults: dict[str, object] = {
        "id": "actors/robert-downey-jr",
        "type": "actor",
        "title": "Robert Downey Jr.",
        "domain": "Movies",
        "owner": Owner.MANUAL,
        "confidence": 0.8,
        "status": "active",
        "aliases": ["RDJ", "Robert Downey"],
        "media_links": MediaLinks(persons=[1], assets=[2]),
        "relationships": [Relationship(type="acted_in", target="movies/iron-man")],
        "sources": ["https://example.test/rdj"],
    }
    defaults.update(overrides)
    return Entity(**defaults)  # type: ignore[arg-type]


def test_upsert_from_vault_creates_entity_and_children(db_session: Session) -> None:
    EntityRepository(db_session).upsert_from_vault(_rdj())
    db_session.commit()

    row = db_session.get(KnowledgeEntity, "actors/robert-downey-jr")
    assert row is not None
    assert row.title == "Robert Downey Jr."
    assert row.owner == "manual"
    assert row.confidence == 0.8
    assert row.aliases == ["RDJ", "Robert Downey"]

    relationships = db_session.query(KnowledgeRelationship).filter_by(entity_id=row.id).all()
    assert [(r.type, r.target) for r in relationships] == [("acted_in", "movies/iron-man")]

    sources = db_session.query(KnowledgeSource).filter_by(entity_id=row.id).all()
    assert [s.source for s in sources] == ["https://example.test/rdj"]

    media_links = db_session.query(KnowledgeMediaLink).filter_by(entity_id=row.id).all()
    assert {(link.kind, link.target_id) for link in media_links} == {("person", 1), ("asset", 2)}


def test_upsert_from_vault_replaces_children_without_duplicates(db_session: Session) -> None:
    repository = EntityRepository(db_session)
    repository.upsert_from_vault(_rdj())
    db_session.commit()

    updated = _rdj(
        relationships=[Relationship(type="acted_in", target="movies/oppenheimer")],
        sources=[],
        media_links=MediaLinks(persons=[1], assets=[]),
    )
    repository.upsert_from_vault(updated)
    db_session.commit()

    entity_id = "actors/robert-downey-jr"
    relationships = db_session.query(KnowledgeRelationship).filter_by(entity_id=entity_id).all()
    assert [(r.type, r.target) for r in relationships] == [("acted_in", "movies/oppenheimer")]
    assert db_session.query(KnowledgeSource).filter_by(entity_id=entity_id).count() == 0
    media_links = db_session.query(KnowledgeMediaLink).filter_by(entity_id=entity_id).all()
    assert {(link.kind, link.target_id) for link in media_links} == {("person", 1)}


def test_get_returns_none_for_unknown_id(db_session: Session) -> None:
    assert EntityRepository(db_session).get("actors/nobody") is None


def test_find_by_alias_matches_exact_alias_not_substring(db_session: Session) -> None:
    repository = EntityRepository(db_session)
    repository.upsert_from_vault(_rdj())
    db_session.commit()

    matches = repository.find_by_alias("RDJ")
    assert [row.id for row in matches] == ["actors/robert-downey-jr"]

    # "DJ" is a substring of the JSON-encoded "RDJ" but not an alias of its own —
    # the quote-bounded match must not produce a false positive.
    assert repository.find_by_alias("DJ") == []


def test_search_matches_title_and_alias_with_filters(db_session: Session) -> None:
    repository = EntityRepository(db_session)
    repository.upsert_from_vault(_rdj())
    repository.upsert_from_vault(
        _rdj(
            id="movies/iron-man",
            type="movie",
            title="Iron Man",
            aliases=[],
            relationships=[],
            sources=[],
            media_links=MediaLinks(),
        )
    )
    db_session.commit()

    by_title = repository.search("Iron Man")
    assert [row.id for row in by_title] == ["movies/iron-man"]

    by_alias = repository.search("RDJ")
    assert [row.id for row in by_alias] == ["actors/robert-downey-jr"]

    filtered_out = repository.search("Iron Man", type="actor")
    assert filtered_out == []

    filtered_in = repository.search("Iron Man", type="movie", domain="Movies")
    assert [row.id for row in filtered_in] == ["movies/iron-man"]


def test_delete_removes_entity_and_all_children(db_session: Session) -> None:
    repository = EntityRepository(db_session)
    repository.upsert_from_vault(_rdj())
    db_session.commit()

    repository.delete("actors/robert-downey-jr")
    db_session.commit()

    entity_id = "actors/robert-downey-jr"
    assert db_session.get(KnowledgeEntity, entity_id) is None
    assert db_session.query(KnowledgeRelationship).filter_by(entity_id=entity_id).count() == 0
    assert db_session.query(KnowledgeSource).filter_by(entity_id=entity_id).count() == 0
    assert db_session.query(KnowledgeMediaLink).filter_by(entity_id=entity_id).count() == 0


def test_find_linked_entities_bulk_reverse_lookup(db_session: Session) -> None:
    repository = EntityRepository(db_session)
    repository.upsert_from_vault(_rdj(media_links=MediaLinks(persons=[7], assets=[])))
    repository.upsert_from_vault(
        _rdj(id="actors/robert-de-niro", title="Robert De Niro", media_links=MediaLinks(persons=[9], assets=[]))
    )
    db_session.commit()

    result = repository.find_linked_entities("person", [7, 9, 999])

    assert result[7].id == "actors/robert-downey-jr"
    assert result[9].id == "actors/robert-de-niro"
    assert 999 not in result


def test_find_linked_entities_empty_target_ids_returns_empty_dict(db_session: Session) -> None:
    assert EntityRepository(db_session).find_linked_entities("person", []) == {}


def test_relationship_repository_for_entity_and_referencing(db_session: Session) -> None:
    repository = EntityRepository(db_session)
    repository.upsert_from_vault(_rdj())
    db_session.commit()

    relationships = RelationshipRepository(db_session)
    outgoing = relationships.for_entity("actors/robert-downey-jr")
    assert [(r.type, r.target) for r in outgoing] == [("acted_in", "movies/iron-man")]

    incoming = relationships.referencing("movies/iron-man")
    assert [r.entity_id for r in incoming] == ["actors/robert-downey-jr"]

    assert relationships.for_entity("actors/nobody") == []
    assert relationships.referencing("movies/nobody") == []
