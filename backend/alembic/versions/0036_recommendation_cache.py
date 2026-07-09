"""0036 — recommendation_cache: zwischengespeicherte Empfehlungen (P26 Phase 1)

Reiner Ergebnis-Cache über CLIP-Nachbarn + Wissensgraph — jede Zeile ist aus
``jobs/recommendation_job.py`` neu berechenbar, siehe Kontrakt in
``docs/planning/2026-07-01_p26-recommendation-engine/README.md``. Kein DB-seitiges
``ON DELETE CASCADE`` auf den Asset-FKs (SQLite-FK-Enforcement ist in dieser App aus,
``photofant/db/engine.py``); verwaiste Zeilen nach Asset-Löschung sind unschädlich, da
die Lese-Route (``api/recommendations.py``) aktiv gegen ``asset_instance`` filtert.

Revision ID: 0036
Revises: 0035
Create Date: 2026-07-09
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("recommended_asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "source_asset_id", "recommended_asset_id", name="uq_recommendation_source_target"
        ),
    )
    op.create_index("ix_recommendation_source", "recommendation_cache", ["source_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_source", "recommendation_cache")
    op.drop_table("recommendation_cache")
