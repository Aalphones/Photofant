from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Base, Person


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    """A throw-away SQLite session on disk, seeded with the _unknown person."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(Person(id=1, name="_unknown", is_unknown=True))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
