"""0005 — tag + asset_tag tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
    )
    op.create_index("ix_tag_name", "tag", ["name"], unique=True)

    op.create_table(
        "asset_tag",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False, server_default="auto"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.UniqueConstraint("asset_id", "tag_id", name="uq_asset_tag"),
    )
    op.create_index("ix_asset_tag_asset_id", "asset_tag", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_asset_tag_asset_id", "asset_tag")
    op.drop_table("asset_tag")
    op.drop_index("ix_tag_name", "tag")
    op.drop_table("tag")
