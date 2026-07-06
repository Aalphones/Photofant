"""Brücke von MCP-Tools zu den bestehenden ``api/*.py``-Endpoint-Funktionen.

Ein MCP-Tool ruft eine Endpoint-Coroutine über :func:`run_endpoint` auf. Der
Adapter öffnet dafür eine DB-Session über dieselbe Session-Factory, die auch der
FastAPI-``Depends(get_session)``-Provider nutzt (Muster: ``api/assets.py``), und
gibt sie als ``session``-Argument weiter. Damit bleibt jede Validierung/Logik an
genau einer Stelle — im Endpoint.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session

from photofant.db.session import SessionLocal


@contextmanager
def db_session() -> Iterator[Session]:
    """Öffnet eine DB-Session mit derselben commit/rollback/close-Semantik wie
    der HTTP-``get_session``-Provider — nur außerhalb der FastAPI-Dependency-
    Injection nutzbar (MCP-Tools laufen nicht in einem Request-Scope)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def run_endpoint[Result](
    endpoint: Callable[..., Awaitable[Result]],
    **kwargs: Any,
) -> Result:
    """Ruft eine async Endpoint-Funktion mit einer frisch geöffneten DB-Session auf.

    Die Endpoints erwarten die Session als ``session``-Keyword (ihr
    ``Depends(get_session)``-Parameter heißt so). Alle weiteren Endpoint-Argumente
    (Pfad-/Query-Werte, Pydantic-Request-Objekte) werden als ``kwargs`` übergeben.
    """
    with db_session() as session:
        return await endpoint(session=session, **kwargs)
