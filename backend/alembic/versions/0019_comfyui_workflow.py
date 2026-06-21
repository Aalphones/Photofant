"""0019 — comfyui_workflow table (P8b Phase 2)

Stores workflow template configs: name, category, template path,
input/param bindings (JSON), validation state.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-21
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_table("comfyui_workflow")
