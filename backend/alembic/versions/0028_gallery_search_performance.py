"""0028 — gallery/search performance indexes + FTS5 caption index

Three independent speedups for the 8000+-image library (Galerie-Fetch +
globale Suche performance pass):
- `ix_asset_tag_tag_id` — the tag-filter/facet join in `list_assets` /
  `_compute_facets` filters and groups by `asset_tag.tag_id`; only
  `asset_id` was indexed (migration 0005), so this scanned the whole table.
- `ix_asset_effective_date` — expression index over
  `coalesce(asset.created_at, asset.imported_at)`, the exact expression
  `list_assets` sorts by (`func.coalesce(Asset.created_at, Asset.imported_at)`).
- `asset_caption_fts` — FTS5 external-content virtual table over
  `asset.caption`, replacing the O(library) Python fuzzy-match pass in
  `q_mode=text` (ADR-015 addendum) with a real index. External-content mode
  (`content='asset', content_rowid='id'`) keeps the caption text itself only
  in `asset.caption` — the FTS table only stores the token index — and the
  three triggers below keep it in sync on insert/update/delete.

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

_FTS_TABLE = "asset_caption_fts"


def upgrade() -> None:
    op.execute("CREATE INDEX ix_asset_tag_tag_id ON asset_tag (tag_id)")
    op.execute(
        "CREATE INDEX ix_asset_effective_date ON asset (coalesce(created_at, imported_at))"
    )

    op.execute(
        f"""
        CREATE VIRTUAL TABLE {_FTS_TABLE} USING fts5(
          caption,
          content='asset',
          content_rowid='id',
          tokenize='unicode61 remove_diacritics 2'
        )
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER asset_caption_fts_ai AFTER INSERT ON asset BEGIN
          INSERT INTO {_FTS_TABLE}(rowid, caption) VALUES (new.id, coalesce(new.caption, ''));
        END
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER asset_caption_fts_ad AFTER DELETE ON asset BEGIN
          INSERT INTO {_FTS_TABLE}({_FTS_TABLE}, rowid, caption) VALUES ('delete', old.id, coalesce(old.caption, ''));
        END
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER asset_caption_fts_au AFTER UPDATE OF caption ON asset BEGIN
          INSERT INTO {_FTS_TABLE}({_FTS_TABLE}, rowid, caption) VALUES ('delete', old.id, coalesce(old.caption, ''));
          INSERT INTO {_FTS_TABLE}(rowid, caption) VALUES (new.id, coalesce(new.caption, ''));
        END
        """
    )
    op.execute(
        f"INSERT INTO {_FTS_TABLE}(rowid, caption) SELECT id, coalesce(caption, '') FROM asset"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS asset_caption_fts_au")
    op.execute("DROP TRIGGER IF EXISTS asset_caption_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS asset_caption_fts_ai")
    op.execute(f"DROP TABLE IF EXISTS {_FTS_TABLE}")
    op.execute("DROP INDEX IF EXISTS ix_asset_effective_date")
    op.execute("DROP INDEX IF EXISTS ix_asset_tag_tag_id")
