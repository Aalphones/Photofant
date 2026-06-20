"""0016 — face vector index (sqlite-vec, ArcFace 512-d)

Adds ``vec_face_embedding`` for cosine-similarity search over face embeddings.
Populated from existing ``face.embedding`` BLOBs if any faces already exist.

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from photofant.db.face_vector_index import CREATE_TABLE_SQL, load_vec_extension

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_VEC_TABLE = "vec_face_embedding"


def upgrade() -> None:
    bind = op.get_bind()
    load_vec_extension(bind.connection.dbapi_connection)
    op.execute(CREATE_TABLE_SQL)

    rows = bind.execute(
        sa.text("SELECT id, embedding FROM face WHERE embedding IS NOT NULL")
    ).fetchall()
    for face_id, blob in rows:
        if blob is not None:
            bind.execute(
                sa.text(f"INSERT INTO {_VEC_TABLE}(rowid, embedding) VALUES (:rowid, :embedding)"),
                {"rowid": int(face_id), "embedding": bytes(blob)},
            )


def downgrade() -> None:
    op.execute(f"DROP TABLE IF EXISTS {_VEC_TABLE}")
