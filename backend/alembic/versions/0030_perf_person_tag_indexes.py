"""0030 — perf_person_tag_indexes: Index auf asset_instance.person_id

P32 Phase 1: `GET /persons` (Counts), Galerie-Filter `person_id` und die
Personennamen-Suche filtern über `asset_instance.person_id` — der
Unique-Constraint `(asset_id, person_id)` greift hier nicht (person_id ist
kein Präfix), also fehlte ein eigener Index.

`asset_tag.tag_id` bekommt hier bewusst KEINEN Index mehr: der existiert
bereits seit Migration 0028 (`ix_asset_tag_tag_id`) — nur das ORM-Modell
kannte ihn noch nicht (jetzt in `models.py` nachgetragen).

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_asset_instance_person_id ON asset_instance (person_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_asset_instance_person_id")
