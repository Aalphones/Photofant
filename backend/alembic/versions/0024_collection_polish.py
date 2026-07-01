"""0024 — Alben-Feinschliff: Cover, Beschreibung, manuelle Reihenfolge (P10 Phase 1)

Konzept-Ausbau der manuellen Alben: `collection.description` (Freitext),
`collection.cover_asset_id` (explizit gewähltes Cover statt nur automatischer
Top-4-Vorschau), `collection_item.position` (manuelle Reihenfolge — NULL = nicht
gesetzt, alte Zeilen bleiben unsortiert und landen ans Ende).

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("collection", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("cover_asset_id", sa.Integer(), nullable=True))
    op.create_index("ix_collection_cover_asset_id", "collection", ["cover_asset_id"])
    op.add_column("collection_item", sa.Column("position", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("collection_item", "position")
    op.drop_index("ix_collection_cover_asset_id", table_name="collection")
    op.drop_column("collection", "cover_asset_id")
    op.drop_column("collection", "description")
