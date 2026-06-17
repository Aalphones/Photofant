"""0006 — seed default caption presets (task_token / Florence-2)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-17

Two model-agnostic task_token presets so a caption run has something to pick
before the user creates their own. "Detailliert" is the global default.
"""
from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


_SEED_PRESETS = [
    {
        "name": "Kurz",
        "config": {"task_token": "<CAPTION>", "max_new_tokens": 256, "num_beams": 3},
        "is_default": 0,
    },
    {
        "name": "Detailliert",
        "config": {"task_token": "<DETAILED_CAPTION>", "max_new_tokens": 1024, "num_beams": 3},
        "is_default": 1,
    },
]


def upgrade() -> None:
    caption_preset = sa.table(
        "caption_preset",
        sa.column("name", sa.Text),
        sa.column("model_id", sa.Integer),
        sa.column("config", sa.JSON),
        sa.column("is_default", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    op.bulk_insert(
        caption_preset,
        [
            {
                "name": preset["name"],
                "model_id": None,
                "config": preset["config"],
                "is_default": preset["is_default"],
                "created_at": now,
            }
            for preset in _SEED_PRESETS
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM caption_preset WHERE name IN ('Kurz', 'Detailliert') AND model_id IS NULL")
