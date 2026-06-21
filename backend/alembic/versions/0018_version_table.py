"""0018 — version table for saved edits (P8 Phase 4)

Tracks saved edit versions per asset_instance or face. Exactly one of
instance_id/face_id must be set (XOR constraint). parent_id chains
edits-of-edits. is_current marks the active version for display.

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-21
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("asset_instance.id"), nullable=True),
        sa.Column("face_id", sa.Integer(), sa.ForeignKey("face.id"), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("version.id"), nullable=True),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "(instance_id IS NOT NULL AND face_id IS NULL) OR (instance_id IS NULL AND face_id IS NOT NULL)",
            name="ck_version_xor",
        ),
    )
    op.create_index("ix_version_instance_id", "version", ["instance_id"])
    op.create_index("ix_version_face_id", "version", ["face_id"])


def downgrade() -> None:
    op.drop_index("ix_version_face_id")
    op.drop_index("ix_version_instance_id")
    op.drop_table("version")
