"""0031 — drop pHash columns (P33, ADR-018)

CLIP/Embeddings decken jetzt alle vier bisherigen pHash-Funktionen ab (Import-Dupe-Check,
Dupe-Scan, Trainingsset-Dupes, Face-Crop-Dedupe). Die drei DHash-Trägerspalten fallen weg.

Reihenfolge zwingend: erst die unresolved pHash-only `dupe_candidate`-Rows löschen
(`clip_distance IS NULL` — reine DHash-Funde, die der CLIP-Pfad beim naechsten Scan/Import
neu findet), danach die Spalten droppen. Resolved Rows bleiben unangetastet — sie
unterdrücken über `uq_review_item_pair` die Wiedervorlage bereits entschiedener Paare.

Revision ID: 0031
Revises: 0030
Create Date: 2026-07-06
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM review_item WHERE type = 'dupe_candidate' "
        "AND resolved_at IS NULL AND clip_distance IS NULL"
    )
    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_column("phash")
    with op.batch_alter_table("face") as batch_op:
        batch_op.drop_column("phash")
    with op.batch_alter_table("review_item") as batch_op:
        batch_op.drop_column("phash_distance")


def downgrade() -> None:
    # WARNUNG: Die gelöschten unresolved pHash-only Rows sind nicht wiederherstellbar;
    # alle drei Spalten kommen nullable und leer zurück (keine Daten-Rekonstruktion moeglich).
    with op.batch_alter_table("review_item") as batch_op:
        batch_op.add_column(sa.Column("phash_distance", sa.Integer(), nullable=True))
    with op.batch_alter_table("face") as batch_op:
        batch_op.add_column(sa.Column("phash", sa.Text(), nullable=True))
    with op.batch_alter_table("asset") as batch_op:
        batch_op.add_column(sa.Column("phash", sa.Integer(), nullable=True))
