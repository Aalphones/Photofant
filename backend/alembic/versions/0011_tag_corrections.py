"""0011 — manual correction markers: tag.alias_of, asset_tag.manually_removed, asset.caption_edited

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    rows = bind.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def _index_exists(index: str) -> bool:
    bind = op.get_bind()
    rows = bind.execute(text("SELECT name FROM sqlite_master WHERE type='index'")).fetchall()
    return any(row[0] == index for row in rows)

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tag.alias_of — SQLite can't ALTER TABLE to add FK constraints; idempotent guards for drift
    if not _column_exists("tag", "alias_of"):
        op.add_column("tag", sa.Column("alias_of", sa.Integer(), nullable=True))
    if not _index_exists("ix_tag_alias_of"):
        op.create_index("ix_tag_alias_of", "tag", ["alias_of"])

    if not _column_exists("asset_tag", "manually_removed"):
        op.add_column(
            "asset_tag",
            sa.Column("manually_removed", sa.Boolean(), nullable=False, server_default="0"),
        )

    if not _column_exists("asset", "caption_edited"):
        op.add_column(
            "asset",
            sa.Column("caption_edited", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _column_exists("asset", "caption_edited"):
        op.drop_column("asset", "caption_edited")
    if _column_exists("asset_tag", "manually_removed"):
        op.drop_column("asset_tag", "manually_removed")
    if _index_exists("ix_tag_alias_of"):
        op.drop_index("ix_tag_alias_of", "tag")
    if _column_exists("tag", "alias_of"):
        op.drop_column("tag", "alias_of")
