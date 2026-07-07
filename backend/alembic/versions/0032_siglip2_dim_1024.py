"""0032 — SigLIP2 embedding dimension migration (768 → 1024, P35 / ADR-021, ADR-022)

Der aktive semantic_search-Embedder wechselt von CLIP ViT-L/14 (768-dim) auf
SigLIP2-large-patch16-384 (1024-dim). Die `vec0`-Tabelle ist dimensions-typisiert und
kann nicht in-place umgestellt werden — sie wird gedroppt und leer mit `float[1024]`
neu angelegt.

Übergangs-Invariante (Pflicht): Nach dieser Migration ist **kein** Embedding mehr
vorhanden — alle `asset.clip_embedding` sind NULL und alle `processing_ledger.embedding_done`
sind 0. Das verhindert einen gemischten 768/1024-Zustand, an dem `np.stack` im Dupe-Scan
und `_serialize` in der Suche crashen würden. Der einzige gültige Zustand ist „kein
Embedding" (überall bereits behandelt: 409 NO_EMBEDDING, `WHERE clip_embedding IS NOT NULL`).
Der Re-Embed (P35 Phase 3) füllt neu.

Die Dim-Literale stehen bewusst als Konstanten in dieser Datei (nicht importiert aus
`vector_index.CREATE_TABLE_SQL`), damit die Migration ein unveränderlicher Schnappschuss
bleibt: der Live-Wert von `EMBEDDING_DIM` ist jetzt 1024, aber die 768→1024-Bewegung soll
im Verlauf ehrlich ablesbar bleiben.

Revision ID: 0032
Revises: 0031
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op
from photofant.db.vector_index import load_vec_extension

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

_VEC_TABLE = "vec_asset_embedding"
_NEW_DIM = 1024  # SigLIP2-large-patch16-384
_OLD_DIM = 768  # CLIP ViT-L/14


def _create_vec_table_sql(dim: int) -> str:
    return (
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {_VEC_TABLE} "
        f"USING vec0(embedding float[{dim}] distance_metric=cosine)"
    )


def _recreate_index_and_clear_embeddings(dim: int) -> None:
    """Drop + recreate the (empty) vec0 table at *dim* and wipe all canonical embeddings.

    Establishes the transition invariant: no embedding of the old dimension survives, so
    consumers never see a mixed-dimension state. Requires the sqlite-vec extension on this
    connection (same pattern as migration 0007).
    """
    bind = op.get_bind()
    load_vec_extension(bind.connection.dbapi_connection)

    op.execute(f"DROP TABLE IF EXISTS {_VEC_TABLE}")
    op.execute(_create_vec_table_sql(dim))
    op.execute("UPDATE asset SET clip_embedding = NULL")
    op.execute("UPDATE processing_ledger SET embedding_done = 0")


def upgrade() -> None:
    _recreate_index_and_clear_embeddings(_NEW_DIM)


def downgrade() -> None:
    # WARNUNG: Die 1024-dim SigLIP2-Embeddings sind nach dem Downgrade verloren — der
    # Index kommt leer bei 768 zurück und alle Assets müssen neu embedded werden
    # (keine Rekonstruktion möglich). Symmetrisch zum Upgrade: gleiche NULL/Reset-Invariante.
    _recreate_index_and_clear_embeddings(_OLD_DIM)
