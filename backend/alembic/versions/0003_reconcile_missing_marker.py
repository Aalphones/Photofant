"""0003 — Reconcile: missing-marker on asset_instance

Adds `asset_instance.missing_at` so the FS↔DB reconciliation can record that a
tracked file is known-gone ("als fehlend markieren") without deleting the row.
NULL = present/active; a timestamp = acknowledged-missing (hidden from the next
reconcile scan).

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-16
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asset_instance", sa.Column("missing_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("asset_instance", "missing_at")
