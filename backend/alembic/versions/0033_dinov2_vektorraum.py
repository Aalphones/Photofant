"""0033 — DINOv2 visual-rerank vector space (P37 / ADR-024)

Adds the second, purely visual embedding space next to SigLIP2:
- ``asset.dino_embedding`` (BLOB) — canonical DINOv2 768-dim embedding (deferred column).
- ``processing_ledger.dino_embedding_done`` — per-model finish flag so a library can
  gain the DINOv2 embedding on a rerun without recomputing SigLIP2.
- ``vec_asset_dino`` (vec0 ``float[768]`` cosine) — the searchable index over that BLOB.

Independent of the SigLIP2 space: this migration does **not** touch ``clip_embedding``,
``embedding_done`` or ``vec_asset_embedding``. Existing SigLIP2 data survives untouched;
DINOv2 embeddings are filled by the embedding job or a ``dino_embedding`` rerun.

The vec0 DDL pins ``float[768]`` locally (not imported from ``vector_index``) so the
migration stays an unchanging snapshot even if the live ``DINO_EMBEDDING_DIM`` ever moves.
Guards make every step safe to re-run against a drifted DB.

Revision ID: 0033
Revises: 0032
Create Date: 2026-07-08
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from photofant.db.vector_index import load_vec_extension

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

_VEC_DINO_TABLE = "vec_asset_dino"
_DINO_DIM = 768  # DINOv2-with-registers-base

_CREATE_VEC_DINO_SQL = (
    f"CREATE VIRTUAL TABLE IF NOT EXISTS {_VEC_DINO_TABLE} "
    f"USING vec0(embedding float[{_DINO_DIM}] distance_metric=cosine)"
)


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("asset", "dino_embedding"):
        op.add_column("asset", sa.Column("dino_embedding", sa.LargeBinary(), nullable=True))
    if not _has_column("processing_ledger", "dino_embedding_done"):
        op.add_column(
            "processing_ledger",
            sa.Column("dino_embedding_done", sa.Boolean(), nullable=False, server_default="0"),
        )

    # vec0 index — needs the sqlite-vec extension on this connection (pattern of 0007/0032).
    load_vec_extension(op.get_bind().connection.dbapi_connection)
    op.execute(_CREATE_VEC_DINO_SQL)


def downgrade() -> None:
    # DINOv2 embeddings are lost on downgrade (no reconstruction) — the SigLIP2 space
    # is untouched throughout, so semantic search keeps working.
    # The vec0 module must be loaded to DROP a vec0 virtual table (same as 0032).
    load_vec_extension(op.get_bind().connection.dbapi_connection)
    op.execute(f"DROP TABLE IF EXISTS {_VEC_DINO_TABLE}")
    if _has_column("processing_ledger", "dino_embedding_done"):
        with op.batch_alter_table("processing_ledger") as batch_op:
            batch_op.drop_column("dino_embedding_done")
    if _has_column("asset", "dino_embedding"):
        with op.batch_alter_table("asset") as batch_op:
            batch_op.drop_column("dino_embedding")
