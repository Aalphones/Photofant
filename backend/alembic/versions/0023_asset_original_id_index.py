"""0023 — index on asset.original_id (P21 Phase 1, Stapel-Query)

list_assets now resolves ComfyUI-Edit-Kinder via `Asset.original_id.in_(roots)` on every
gallery page (stack grouping) — without an index this is a full table scan per page.

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_asset_original_id", "asset", ["original_id"])


def downgrade() -> None:
    op.drop_index("ix_asset_original_id", table_name="asset")
