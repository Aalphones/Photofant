"""0043 — asset_embedding: Embedding-BLOBs aus der Asset-Zeile auslagern (Phase 2)

Neue Nebentabelle mit einer Zeile je Bild, die beide Vektoren aufnimmt; der
Bestand aus ``asset.clip_embedding`` / ``asset.dino_embedding`` wird herüberkopiert.
Ab hier liest und schreibt die Zugriffsschicht (``photofant/db/embeddings.py``)
ausschließlich hier. **Die alten Spalten bleiben stehen** — geht in diesem Fenster
etwas schief, reicht ein Rücksetzen des Codes ohne Datenverlust. Migration 0044
(Plan-Phase 3) droppt sie dann und gibt den Platz frei.

Kein DB-seitiges ``ON DELETE CASCADE`` auf dem Asset-FK: SQLite-FK-Enforcement ist
in dieser App aus (``photofant/db/engine.py``). Die Nebenzeile stirbt nicht von
selbst, wenn ein Asset gelöscht wird — die Löschstelle (``media/moves.py``) räumt
sie über die Zugriffsschicht mit ab.

Kontrakt: ``docs/planning/2026-07-21_asset-embeddings-auslagern.md`` (Phase 2).

Revision ID: 0043
Revises: 0042
Create Date: 2026-07-23
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("asset_embedding"):
        op.create_table(
            "asset_embedding",
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), primary_key=True),
            sa.Column("clip_embedding", sa.LargeBinary(), nullable=True),
            sa.Column("dino_embedding", sa.LargeBinary(), nullable=True),
        )

    # Bestand herüberkopieren. ``NOT IN`` macht den Copy re-run-sicher: ein zweiter
    # Lauf (abgebrochene Migration, Re-Apply) fügt nur fehlende Zeilen nach, statt
    # an der PK-Kollision zu scheitern.
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO asset_embedding (asset_id, clip_embedding, dino_embedding)
            SELECT id, clip_embedding, dino_embedding
            FROM asset
            WHERE (clip_embedding IS NOT NULL OR dino_embedding IS NOT NULL)
              AND id NOT IN (SELECT asset_id FROM asset_embedding)
            """
        )
    )


def downgrade() -> None:
    if _has_table("asset_embedding"):
        op.drop_table("asset_embedding")
