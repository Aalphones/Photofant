"""FTS5 full-text index over asset captions (Galerie/Suche performance pass).

The searchable index is an FTS5 external-content virtual table
(`asset_caption_fts`) living in the main DB; its rowid is `asset.id`. The
canonical caption text is `asset.caption` — this table only stores the token
index, kept in sync via the AFTER INSERT/UPDATE/DELETE triggers created in
migration 0028, so any drift between the two is forward-recoverable by
rebuilding the table from `asset.caption` (see migration for the initial
backfill; there is no live rebuild helper yet — there is no BLOB-style write
path here to drift, only trigger-fed rows).
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

_TABLE = "asset_caption_fts"


def _index_available(session: Session) -> bool:
    """True if the FTS5 table exists on this connection.

    The index is a rebuildable secondary structure created only by the
    migration (it is not part of `Base.metadata`). Connections without the
    migration applied — e.g. throw-away test DBs — degrade gracefully instead
    of crashing (caller falls back to `Asset.caption.ilike(...)`).
    """
    row = session.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": _TABLE},
    ).first()
    return row is not None


def _sanitize_query(query: str) -> str:
    """Turn free-text user input into a safe FTS5 MATCH query.

    Raw user input can contain FTS5 query syntax (`"`, `*`, `AND`, `OR`,
    `NEAR`, ...) that would raise `OperationalError` if passed through
    unescaped. Each whitespace-separated token is wrapped in double quotes
    (escaping internal `"` by doubling it, the SQLite string-literal
    convention) and suffixed with `*` for prefix matching, e.g. the query
    `black hair` becomes `"black"* "hair"*` — an implicit AND across tokens.
    """
    tokens = query.split()
    quoted_tokens = [f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens]
    return " ".join(quoted_tokens)


def search_caption_asset_ids(session: Session, query: str) -> list[int] | None:
    """Return asset IDs whose caption matches *query*, or `None` if the index is missing.

    `None` signals the caller (`list_assets`) to fall back to
    `Asset.caption.ilike(f"%{query}%")` instead. An empty (whitespace-only)
    query yields an empty list, not `None` — the index is available, there
    are just no tokens to search for.
    """
    if not _index_available(session):
        log.warning("Caption FTS index missing — caller should fall back to ILIKE")
        return None

    sanitized_query = _sanitize_query(query)
    if not sanitized_query:
        return []

    rows = session.execute(
        text(f"SELECT rowid FROM {_TABLE} WHERE {_TABLE} MATCH :q"),
        {"q": sanitized_query},
    ).fetchall()
    return [int(row[0]) for row in rows]
