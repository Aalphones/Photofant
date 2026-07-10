"""0037 — knowledge_changelog: Explainability-Log jeder Feld-Korrektur (P25 Phase 3)

Herkunfts-Metadaten einer Änderung (was/warum/wer/wann), nicht der neue Wert selbst —
der lebt im Markdown-Vault + in den ``knowledge_*``-Cache-Spalten aus Migration 0034.
Reiner Arbeitszustand wie ``knowledge_tasks`` (0035); die Explainability-UI (Dok 020 §14)
braucht ihn abfrag-/joinbar. ``old_value``/``new_value`` sind JSON, weil das gepatchte
Feld skalar (``title``) oder strukturiert (``relationships``) sein kann.

Revision ID: 0037
Revises: 0036
Create Date: 2026-07-10
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_changelog",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_id", sa.Text(), sa.ForeignKey("knowledge_entities.id"), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_changelog_entity_id", "knowledge_changelog", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_changelog_entity_id", "knowledge_changelog")
    op.drop_table("knowledge_changelog")
