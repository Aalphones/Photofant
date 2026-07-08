"""0035 — knowledge_tasks: Aufgaben-Queue für „hier fehlt Wissen" (P23 Phase 1)

Reiner Arbeitszustand, kein Vault-Wissen (Gegenstück zu den ``knowledge_*``-Cache-Tabellen
aus Migration 0034, die den Markdown-Vault spiegeln). Dedup läuft anwendungsseitig über
``kind`` + ``context``-Gleichheit unter offenen Aufgaben — siehe Kontrakt in
``docs/planning/2026-07-01_p23-knowledge-wizard/README.md``.

Revision ID: 0035
Revises: 0034
Create Date: 2026-07-08
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("context", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_knowledge_tasks_kind", "knowledge_tasks", ["kind"])
    op.create_index("ix_knowledge_tasks_status", "knowledge_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_tasks_status", "knowledge_tasks")
    op.drop_index("ix_knowledge_tasks_kind", "knowledge_tasks")
    op.drop_table("knowledge_tasks")
