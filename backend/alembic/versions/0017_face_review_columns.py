"""0017 — face review columns on review_item

Adds ``face_id``, ``suggested_person_id``, ``score`` to support
face-suggestion review items (type='face_suggestion') alongside
existing dupe_candidate rows.

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_item", sa.Column("face_id", sa.Integer(), nullable=True))
    op.add_column("review_item", sa.Column("suggested_person_id", sa.Integer(), nullable=True))
    op.add_column("review_item", sa.Column("score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("review_item", "score")
    op.drop_column("review_item", "suggested_person_id")
    op.drop_column("review_item", "face_id")
