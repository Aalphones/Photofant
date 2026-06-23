"""0020 — prompt_template table (P9 Phase 4)

Stores reusable Flux2-Edit prompt templates with name, prompt text,
and parameter presets (strength, steps, guidance, seed).

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-23
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # Seed 2–3 useful default templates
    op.execute(
        """
        INSERT INTO prompt_template (name, prompt, params) VALUES
        ('Portrait verbessern', 'a beautiful portrait photo of {person}, sharp focus, professional lighting, 8k', '{"strength": 0.55, "steps": 25, "guidance": 7.5, "seed": -1}'),
        ('Anime-Stil', '{person} in anime style, vibrant colors, detailed illustration', '{"strength": 0.7, "steps": 30, "guidance": 8.0, "seed": -1}'),
        ('Hintergrund entfernen', 'plain white background, studio photo of {person}', '{"strength": 0.6, "steps": 20, "guidance": 7.0, "seed": -1}')
        """
    )


def downgrade() -> None:
    op.drop_table("prompt_template")
