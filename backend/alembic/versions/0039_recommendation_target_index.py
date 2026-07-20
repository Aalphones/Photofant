"""0039 — recommendation_cache: Index auf recommended_asset_id

`invalidate_recommendations` (`jobs/recommendation_job.py`, Plan
`2026-07-20_recommendation-cache-invalidation` Phase 1) filtert erstmals auf
`recommended_asset_id` (Cache-Zeile ist auch stale, wenn nur die Ziel-Seite eines Paares
sich ändert). Projekt-Konvention „Filter-Spalten kriegen ihren Index im selben Change"
(`docs/conventions/python.md`) — ohne Index wäre das ein Full-Table-Scan auf
`recommendation_cache` bei jeder Invalidierung.

Revision ID: 0039
Revises: 0038
Create Date: 2026-07-20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def _has_index(table: str, index: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return insp.has_table(table) and index in {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    if not _has_index("recommendation_cache", "ix_recommendation_target"):
        op.create_index(
            "ix_recommendation_target", "recommendation_cache", ["recommended_asset_id"]
        )


def downgrade() -> None:
    if _has_index("recommendation_cache", "ix_recommendation_target"):
        op.drop_index("ix_recommendation_target", table_name="recommendation_cache")
