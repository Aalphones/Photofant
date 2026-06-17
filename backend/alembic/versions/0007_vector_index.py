"""0007 — vector index (sqlite-vec) + embedding ledger flag + caption-preset FK

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-17

Adds the CLIP semantic-search infrastructure (ADR-001):
- `processing_ledger.embedding_done` — once-only guarantee for the embedding step
- `vec_asset_embedding` — sqlite-vec vec0 virtual table (rowid = asset.id)
- formalizes the long-planned `asset.caption_preset_id` → `caption_preset.id` FK
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from photofant.db.vector_index import CREATE_TABLE_SQL, load_vec_extension

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_VEC_TABLE = "vec_asset_embedding"


def upgrade() -> None:
    op.add_column(
        "processing_ledger",
        sa.Column("embedding_done", sa.Boolean(), nullable=False, server_default="0"),
    )

    # The caption_preset_id column already exists (migration 0002); attach the FK now.
    with op.batch_alter_table("asset") as batch_op:
        batch_op.create_foreign_key(
            "fk_asset_caption_preset", "caption_preset", ["caption_preset_id"], ["id"]
        )

    # vec0 virtual table — needs the sqlite-vec extension loaded on this connection.
    bind = op.get_bind()
    load_vec_extension(bind.connection.dbapi_connection)
    op.execute(CREATE_TABLE_SQL)


def downgrade() -> None:
    op.execute(f"DROP TABLE IF EXISTS {_VEC_TABLE}")

    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_constraint("fk_asset_caption_preset", type_="foreignkey")

    op.drop_column("processing_ledger", "embedding_done")
