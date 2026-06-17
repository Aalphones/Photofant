"""0012 — collections: collection, smart_trigger, collection_item (Konzept §5)

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        # album | training_set | smart_album — training_set schema only (P10)
        sa.Column("kind", sa.Text(), nullable=False, server_default="album"),
        # smart_album only: any (ODER) | all (UND)
        sa.Column("match_mode", sa.Text(), nullable=False, server_default="any"),
        sa.Column("settings", sa.JSON(), nullable=True),
    )

    op.create_table(
        "smart_trigger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("collection.id"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),  # person | tag | caption
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("person.id"), nullable=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), nullable=True),
        sa.Column("phrase", sa.Text(), nullable=True),
        sa.Column("negate", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index("ix_smart_trigger_collection_id", "smart_trigger", ["collection_id"])

    op.create_table(
        "collection_item",
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("collection.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),  # manual | smart
        sa.Column("caption_override", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("collection_id", "asset_id", name="pk_collection_item"),
    )
    op.create_index("ix_collection_item_asset_id", "collection_item", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_collection_item_asset_id", "collection_item")
    op.drop_table("collection_item")
    op.drop_index("ix_smart_trigger_collection_id", "smart_trigger")
    op.drop_table("smart_trigger")
    op.drop_table("collection")
