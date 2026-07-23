"""0044 — asset: LEGACY-Embedding-Spalten entfernen (Phase 3)

Droppt ``asset.clip_embedding`` und ``asset.dino_embedding``. Seit Migration
0043 schreibt kein Code mehr in diese Spalten — die Zugriffsschicht
(``photofant/db/embeddings.py``) ist der einzige Schreiber, und sie schreibt
ausschließlich in die Nebentabelle ``asset_embedding``. Der Copy in 0043 ist
damit ein stabiler Snapshot; dieses Droppen verliert keine Daten.

SQLite kennt kein natives ``DROP COLUMN`` über die Alembic-Standardroute —
``batch_alter_table`` baut die Tabelle dafür neu (Copy-Rename-Pattern).

**Das ``ANALYZE`` am Ende ist nicht optional** — gleiche Falle wie Migration
0041: ohne neue Tabellen-Statistiken plant SQLite weiter mit der alten
Tabellengröße (~90 MB), der Geschwindigkeitsgewinn bleibt aus, obwohl die
Spalten weg sind.

Kontrakt: ``docs/planning/2026-07-21_asset-embeddings-auslagern.md`` (Phase 3).

Revision ID: 0044
Revises: 0043
Create Date: 2026-07-23
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("asset") as batch_op:
        batch_op.drop_column("clip_embedding")
        batch_op.drop_column("dino_embedding")
    # Vollständiges ANALYZE, bewusst ohne PRAGMA analysis_limit — siehe Migration
    # 0041: mit dem Limit bleiben die Schätzungen zu grob, der Planer bemerkt die
    # neue (kleine) Tabellengröße nicht. Bei 10.000er Bestand < 1 s.
    op.execute("ANALYZE")


def downgrade() -> None:
    # Stellt die Spalten leer wieder her — die Werte sind mit dem Drop weg. Ein
    # echtes Zurückrollen der Daten bräuchte den Copy aus asset_embedding; nicht
    # Teil dieser Migration, weil ab 0043 kein Code mehr dorthin schreibt (siehe
    # Docstring oben) und ein Rollback dieser Phase nur die Spalten selbst betrifft.
    with op.batch_alter_table("asset") as batch_op:
        batch_op.add_column(sa.Column("clip_embedding", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("dino_embedding", sa.LargeBinary(), nullable=True))
    op.execute("ANALYZE")
