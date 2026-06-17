"""0011 — manual correction markers: tag.alias_of, asset_tag.manually_removed, asset.caption_edited

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tag.alias_of — points to the canonical tag; set by POST /api/tags/merge
    op.add_column("tag", sa.Column("alias_of", sa.Integer(), sa.ForeignKey("tag.id"), nullable=True))
    op.create_index("ix_tag_alias_of", "tag", ["alias_of"])

    # asset_tag.manually_removed — prevents auto-tagger from re-adding an explicitly removed tag
    op.add_column(
        "asset_tag",
        sa.Column("manually_removed", sa.Boolean(), nullable=False, server_default="0"),
    )

    # asset.caption_edited — prevents captioner from overwriting a manually edited caption
    op.add_column(
        "asset",
        sa.Column("caption_edited", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("asset", "caption_edited")
    op.drop_column("asset_tag", "manually_removed")
    op.drop_index("ix_tag_alias_of", "tag")
    op.drop_column("tag", "alias_of")
