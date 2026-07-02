"""0026 — Person: Gruppenfeld + Erstellungsdatum (P29)

Fügt `person.group_name` (Freitext-Gruppe) und `person.created_at` hinzu.
Kein Backfill für bestehende Zeilen — beide Felder bleiben `NULL`, Sortierung
nach Erstellungsdatum behandelt NULL als "ältest".

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("person", sa.Column("group_name", sa.Text(), nullable=True))
    op.add_column("person", sa.Column("created_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("person") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("group_name")
