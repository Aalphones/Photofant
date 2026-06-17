"""0008 — heuristics_done flag in processing_ledger

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-17

Adds the quality-heuristics step flag:
- `processing_ledger.heuristics_done` — once-only guarantee for the heuristics step
  (quality_score, framing) so the step is skippable on rerun.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "processing_ledger",
        sa.Column("heuristics_done", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("processing_ledger", "heuristics_done")
