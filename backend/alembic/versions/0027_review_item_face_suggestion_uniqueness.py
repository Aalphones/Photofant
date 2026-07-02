"""0027 — fix review_item uniqueness for face suggestions

The old `uq_review_item_pair` unique constraint on (type, asset_a_id,
asset_b_id) was designed for dupe_candidate rows (distinct asset pairs).
face_suggestion rows reuse the same columns with asset_a_id == asset_b_id
(both set to the face's asset), so a photo with two or more faces needing
review could only ever get ONE suggestion row — every following insert hit
the unique constraint (sqlite3.IntegrityError).

Splits the single constraint into two partial unique indexes:
- uq_review_item_pair: (type, asset_a_id, asset_b_id) WHERE face_id IS NULL
  — keeps the original dupe_candidate guarantee untouched.
- uq_review_item_face_pending: (face_id) WHERE type = 'face_suggestion'
  AND resolved_at IS NULL — at most one pending suggestion per face, but
  allows a new one after the previous suggestion was confirmed/rejected.

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("review_item") as batch_op:
        batch_op.drop_constraint("uq_review_item_pair", type_="unique")

    op.create_index(
        "uq_review_item_pair",
        "review_item",
        ["type", "asset_a_id", "asset_b_id"],
        unique=True,
        sqlite_where=sa.text("face_id IS NULL"),
    )
    op.create_index(
        "uq_review_item_face_pending",
        "review_item",
        ["face_id"],
        unique=True,
        sqlite_where=sa.text("type = 'face_suggestion' AND resolved_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_review_item_face_pending", table_name="review_item")
    op.drop_index("uq_review_item_pair", table_name="review_item")

    with op.batch_alter_table("review_item") as batch_op:
        batch_op.create_unique_constraint(
            "uq_review_item_pair", ["type", "asset_a_id", "asset_b_id"]
        )
