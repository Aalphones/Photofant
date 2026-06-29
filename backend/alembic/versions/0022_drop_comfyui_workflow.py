"""0022 — drop comfyui_workflow table (P16 Phase 2)

Workflows are now discovered from the filesystem (.photofant/workflows/*.json).
The DB-backed registry (upload, activate, validate) is removed.

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-29
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("comfyui_workflow")


def downgrade() -> None:
    op.create_table(
        "comfyui_workflow",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False, server_default="generic"),
        sa.Column("template_path", sa.Text(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("params", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
