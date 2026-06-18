"""0002 — Galerie-MVP Schema: person, asset, asset_instance, processing_ledger

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-15
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("is_unknown", sa.Boolean(), nullable=False, server_default="0"),
    )

    op.create_table(
        "asset",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("content_hash", sa.Text(), unique=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("format", sa.Text(), nullable=True),
        sa.Column("framing", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("captioner", sa.Text(), nullable=True),
        sa.Column("caption_preset_id", sa.Integer(), nullable=True),  # FK to caption_preset, added in P4
        sa.Column("tagger", sa.Text(), nullable=True),
        sa.Column("generation_meta", sa.JSON(), nullable=True),
        sa.Column("clip_embedding", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_asset_content_hash", "asset", ["content_hash"], unique=True)
    op.create_index("ix_asset_created_at", "asset", ["created_at"])

    op.create_table(
        "asset_instance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("person.id"), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("favourite", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("fixed_person", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("asset_id", "person_id", name="uq_instance_asset_person"),
    )
    op.create_index("ix_asset_instance_deleted_at", "asset_instance", ["deleted_at"])

    op.create_table(
        "processing_ledger",
        sa.Column("content_hash", sa.Text(), primary_key=True),
        sa.Column("faces_done", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("tags_done", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("caption_done", sa.Boolean(), nullable=False, server_default="0"),
    )

    op.execute("INSERT INTO person (name, is_unknown) VALUES ('_unknown', 1)")


def downgrade() -> None:
    op.drop_table("processing_ledger")
    op.drop_index("ix_asset_instance_deleted_at", "asset_instance")
    op.drop_table("asset_instance")
    op.drop_index("ix_asset_created_at", "asset")
    op.drop_index("ix_asset_content_hash", "asset")
    op.drop_table("asset")
    op.drop_table("person")
