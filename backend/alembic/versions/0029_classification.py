"""0029 — Bildklassifizierung: classification_category/_label/_asset (P18 Phase 1)

Legt die drei Tabellen für die WD14+CLIP-Regel-Engine an (Konzept: „Metadaten-
Kategorien") und seedet den Konzept-Katalog (Kategorien + Labels, `builtin=1`).

`ProcessingLedger.classified` (bereits seit Migration 0009 vorhanden, bis hierhin
ungenutzt) wird ab dieser Phase belegt — keine neue Ledger-Spalte nötig.

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from photofant.classification.seed import insert_seed_catalog

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classification_category",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("mode", sa.Text(), nullable=False),  # single | multi
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("builtin", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("min_confidence", sa.Float(), nullable=True),
    )

    op.create_table(
        "classification_label",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("classification_category.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("clip_prompts", sa.JSON(), nullable=True),
        sa.Column("wd14_tags", sa.JSON(), nullable=True),
        sa.UniqueConstraint("category_id", "name", name="uq_classification_label_category_name"),
    )
    op.create_index(
        "ix_classification_label_category_id", "classification_label", ["category_id"]
    )

    op.create_table(
        "asset_classification",
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column(
            "label_id",
            sa.Integer(),
            sa.ForeignKey("classification_label.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id", sa.Integer(), sa.ForeignKey("classification_category.id"), nullable=False,
        ),  # denormalisiert für Filter/Facets
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),  # clip | wd14 | fused
        sa.PrimaryKeyConstraint("asset_id", "label_id", name="pk_asset_classification"),
    )
    op.create_index(
        "ix_asset_classification_asset_id", "asset_classification", ["asset_id"]
    )
    op.create_index(
        "ix_asset_classification_category_id", "asset_classification", ["category_id"]
    )

    insert_seed_catalog(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_asset_classification_category_id", "asset_classification")
    op.drop_index("ix_asset_classification_asset_id", "asset_classification")
    op.drop_table("asset_classification")
    op.drop_index("ix_classification_label_category_id", "classification_label")
    op.drop_table("classification_label")
    op.drop_table("classification_category")
