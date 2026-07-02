"""0025 — CLIP-Distanz für duale Duplikaterkennung (ADR-007)

Macht `review_item.phash_distance` nullable (CLIP-only Treffer haben keinen
DHash-Wert) und fügt `review_item.clip_distance` hinzu (Cosine-Distance,
NULL wenn nur DHash ausgelöst hat).

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("review_item") as batch_op:
        batch_op.alter_column("phash_distance", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("clip_distance", sa.Float(), nullable=True))


def downgrade() -> None:
    # WARNUNG: Rows, die nur per CLIP gefunden wurden (phash_distance IS NULL),
    # verlieren beim Downgrade ihre Duplikat-Info — NOT NULL erzwingt einen Platzhalterwert.
    with op.batch_alter_table("review_item") as batch_op:
        batch_op.drop_column("clip_distance")
        batch_op.alter_column("phash_distance", existing_type=sa.Integer(), nullable=False)
