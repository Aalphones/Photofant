"""0040 — knowledge_entities.attributes: Merkmale im Cache spiegeln (P38 Phase 2)

Merkmale (Geburtstag, Beruf, …) leben ab P38 als eigener Frontmatter-Block mit Owner
pro Merkmal. Die Markdown-Datei bleibt die Wahrheit (ADR-025) — diese Spalte ist eine
reine Spiegelung wie ``aliases``, damit Listen-Ansichten (Personen-Liste, Wissens-
Übersicht) den Vollständigkeits-Wert aus einem Query beantworten können, statt pro
Zeile eine Markdown-Datei zu öffnen. Der Vollständigkeits-Wert selbst wird **nicht**
gespeichert, sondern immer aus Merkmalen + Domänen-Felddefinitionen berechnet.

Bestehende Zeilen bekommen ``{}`` und füllen sich beim nächsten Reconcile/Schreiben.

Revision ID: 0040
Revises: 0039
Create Date: 2026-07-21
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return insp.has_table(table) and column in {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    if not _has_column("knowledge_entities", "attributes"):
        op.add_column(
            "knowledge_entities",
            sa.Column("attributes", sa.JSON(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    if _has_column("knowledge_entities", "attributes"):
        op.drop_column("knowledge_entities", "attributes")
