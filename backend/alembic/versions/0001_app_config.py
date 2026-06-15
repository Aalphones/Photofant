"""0001 — app_config Tabelle anlegen

Revision ID: 0001
Revises:
Create Date: 2026-06-15
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("key", sa.Text(), nullable=False, primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("app_config")
