from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from photofant.classification.seed import SEED_CATALOG, insert_seed_catalog
from photofant.db.models import Base, ClassificationCategory, ClassificationLabel


@pytest.fixture
def classification_db(tmp_path) -> Generator[Session, None, None]:
    """Frische DB, Schema neu angelegt, Seed-Katalog eingespielt (wie die Migration es tut)."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        insert_seed_catalog(conn)

    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_seed_categories_match_catalog(classification_db: Session) -> None:
    category_count = classification_db.scalar(select(func.count()).select_from(ClassificationCategory))
    assert category_count == len(SEED_CATALOG)


def test_seed_categories_are_builtin_and_enabled(classification_db: Session) -> None:
    categories = classification_db.scalars(select(ClassificationCategory)).all()
    assert all(category.builtin for category in categories)
    assert all(category.enabled for category in categories)


def test_seed_labels_match_catalog(classification_db: Session) -> None:
    expected_label_count = sum(len(category.labels) for category in SEED_CATALOG)
    label_count = classification_db.scalar(select(func.count()).select_from(ClassificationLabel))
    assert label_count == expected_label_count


def test_seed_label_sample_anime_has_wd14_tag(classification_db: Session) -> None:
    stil_category = classification_db.scalar(
        select(ClassificationCategory).where(ClassificationCategory.name == "Stil")
    )
    assert stil_category is not None
    assert stil_category.mode == "multi"

    anime_label = classification_db.scalar(
        select(ClassificationLabel).where(
            ClassificationLabel.category_id == stil_category.id,
            ClassificationLabel.name == "Anime",
        )
    )
    assert anime_label is not None
    assert anime_label.wd14_tags == ["anime"]
    assert anime_label.clip_prompts is None


def test_seed_single_multi_mode_matches_konzept(classification_db: Session) -> None:
    expected_single = {"Medium", "Realismus", "Franchise", "Charakter", "Künstler", "AI-Modell"}
    expected_multi = {"Stil", "Motiv", "Szene", "Eigenschaften", "Technik"}

    categories = classification_db.scalars(select(ClassificationCategory)).all()
    single_names = {category.name for category in categories if category.mode == "single"}
    multi_names = {category.name for category in categories if category.mode == "multi"}

    assert single_names == expected_single
    assert multi_names == expected_multi
