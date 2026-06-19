"""0014 — pHash + review_item: Duplikaterkennungs-Infra

Fügt zwei neue Spalten zu `asset` hinzu (phash, original_id) und legt die
Tabelle `review_item` für die manuell zu entscheidenden Duplikat-Paare an.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-19
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    existing_cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(asset)")).fetchall()}
    if "phash" not in existing_cols:
        op.add_column("asset", sa.Column("phash", sa.Integer(), nullable=True))
    # SQLite: ForeignKey in add_column triggers unsupported ALTER CONSTRAINT — plain Integer is fine,
    # SQLite doesn't enforce FK constraints unless PRAGMA foreign_keys=ON is set per connection.
    if "original_id" not in existing_cols:
        op.add_column("asset", sa.Column("original_id", sa.Integer(), nullable=True))

    existing_tables = {
        row[0]
        for row in bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    }
    if "review_item" in existing_tables:
        return

    op.create_table(
        "review_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("asset_a_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("asset_b_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("phash_distance", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.UniqueConstraint("type", "asset_a_id", "asset_b_id", name="uq_review_item_pair"),
    )


def downgrade() -> None:
    op.drop_table("review_item")
    op.drop_column("asset", "original_id")
    op.drop_column("asset", "phash")
