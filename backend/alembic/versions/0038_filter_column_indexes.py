"""0038 — filter_column_indexes: fehlende Indizes auf tatsächlich gefilterten Spalten

Schema-Audit (2026-07-20): welche Spalten die Galerie-/Review-/Klassifikations-Filter
per `.where()`/`.filter()` wirklich anfassen, aber noch keinen Index haben.

- `ix_asset_source` / `ix_asset_framing` — Galerie-Filter „Quelle"/„Framing"
  (`list_assets`, `assets.py`), bisher Full-Table-Scan auf der Asset-Tabelle.
- `ix_asset_instance_favourite` — Galerie-Filter „Favoriten" (`assets.py`).
- `ix_review_item_type_resolved_at` — Review-Queue-Listen filtern durchgängig auf
  `type` + `resolved_at` zusammen (`review.py`, `review_queue.py`); die beiden
  bestehenden Indizes sind partial-unique auf andere Bedingungen gemünzt und
  bedienen dieses Paar nicht.
- `ix_asset_classification_label_id` — `label_id` wird beim Kategorie-/Label-Löschen
  einzeln gefiltert (`classification.py`); der Primärkey `(asset_id, label_id)`
  deckt das nicht, weil `asset_id` vorne steht.

Bewusst NICHT indiziert: `caption_preset.model_id`, `person.is_unknown`,
`model_registry.enabled`, `knowledge_media_links.kind/target_id`,
`version.is_current` — alles Tabellen mit Handvoll bis einstelliger Zeilenzahl,
ein Index wäre dort reiner Schreib-Overhead ohne Lesenutzen.

Revision ID: 0038
Revises: 0037
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_asset_source ON asset (source)")
    op.execute("CREATE INDEX ix_asset_framing ON asset (framing)")
    op.execute("CREATE INDEX ix_asset_instance_favourite ON asset_instance (favourite)")
    op.execute(
        "CREATE INDEX ix_review_item_type_resolved_at ON review_item (type, resolved_at)"
    )
    op.execute(
        "CREATE INDEX ix_asset_classification_label_id ON asset_classification (label_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_asset_classification_label_id")
    op.execute("DROP INDEX IF EXISTS ix_review_item_type_resolved_at")
    op.execute("DROP INDEX IF EXISTS ix_asset_instance_favourite")
    op.execute("DROP INDEX IF EXISTS ix_asset_framing")
    op.execute("DROP INDEX IF EXISTS ix_asset_source")
