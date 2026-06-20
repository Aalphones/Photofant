"""0015 — face table: Detection, Embedding, Crop-Provenienz

Legt die `face`-Tabelle an (Konzept §5). Enthält zusätzlich `score` (REAL)
und `age` (INTEGER) für FaceDto — nicht im Konzept-DDL, aber vom Kontrakt
verlangt.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = {
        row[0]
        for row in bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    }
    if "face" in existing_tables:
        return

    op.create_table(
        "face",
        sa.Column("id", sa.Integer(), primary_key=True),
        # NULL = eigenständiges Face ohne Original (P7 Phase 6)
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=True),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("person.id"), nullable=True),
        # source_version_id: FK auf version-Tabelle (kommt in P8) — als plain INT bis dahin
        sa.Column("source_version_id", sa.Integer(), nullable=True),
        sa.Column("crop_path", sa.Text(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("padding", sa.Integer(), nullable=True),
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
        sa.Column("phash", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),   # detection confidence
        sa.Column("age", sa.Integer(), nullable=True),   # aus buffalo_l genderage
        sa.Column("origin", sa.Text(), nullable=True),   # derived | manual_original
        sa.Column("origin_type", sa.Text(), nullable=True),  # original | upscale | flux_edit
        sa.Column("is_upscaled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("resolution", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_face_asset_id", "face", ["asset_id"])
    op.create_index("ix_face_person_id", "face", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_face_person_id", table_name="face")
    op.drop_index("ix_face_asset_id", table_name="face")
    op.drop_table("face")
