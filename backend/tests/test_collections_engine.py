"""Regression: `_insert_smart_member` muss ueber die ON-CONFLICT-Klausel idempotent bleiben,
auch nachdem 0042 den zusammengesetzten PK durch einen partiellen Unique-Index ersetzt hat
(ADR-035, Face-Support). Der partielle Index ist als Konflikt-Ziel nur erkennbar, wenn die
`WHERE`-Bedingung im `ON CONFLICT` mitgeschickt wird — sonst wirft SQLite
'ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint'.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from photofant.collections.engine import _insert_smart_member, evaluate_asset
from photofant.db.models import Asset, AssetInstance, Collection, CollectionItem, SmartTrigger, Tag


def _seed_asset(session: Session, *, content_hash: str) -> Asset:
    asset = Asset(content_hash=content_hash, source="original")
    session.add(asset)
    session.flush()
    session.add(AssetInstance(asset_id=asset.id, person_id=1, path=f"/tmp/{content_hash}.jpg"))
    session.commit()
    return asset


def test_insert_smart_member_is_idempotent(db_session: Session) -> None:
    """Zwei Inserts fuer dieselbe (collection_id, asset_id)-Kombi duerfen nicht crashen —
    genau der Fall, wenn zwei Worker (Tagging/Captioning) denselben Asset gleichzeitig
    neu bewerten und beide versuchen, ihn in dieselbe Smart Collection einzutragen."""
    collection = Collection(id=1, name="Smart", kind="smart_album")
    db_session.add(collection)
    db_session.commit()
    asset = _seed_asset(db_session, content_hash="a")

    _insert_smart_member(db_session, collection.id, asset.id)
    db_session.commit()
    _insert_smart_member(db_session, collection.id, asset.id)
    db_session.commit()

    rows = db_session.query(CollectionItem).filter_by(collection_id=collection.id, asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].source == "smart"


def test_evaluate_asset_adds_smart_match(db_session: Session) -> None:
    """End-to-End: ein Tag-Trigger zieht einen passenden Asset automatisch in die Smart Collection."""
    collection = Collection(id=1, name="Smart", kind="smart_album", match_mode="any")
    tag = Tag(id=1, name="urlaub")
    db_session.add_all([collection, tag])
    db_session.commit()
    db_session.add(SmartTrigger(collection_id=collection.id, type="tag", tag_id=tag.id))
    db_session.commit()

    asset = _seed_asset(db_session, content_hash="a")
    from photofant.db.models import AssetTag

    db_session.add(AssetTag(asset_id=asset.id, tag_id=tag.id))
    db_session.commit()

    evaluate_asset(db_session, asset.id)
    db_session.commit()

    rows = db_session.query(CollectionItem).filter_by(collection_id=collection.id, asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].source == "smart"
