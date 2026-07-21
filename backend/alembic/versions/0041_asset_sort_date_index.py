"""0041 — asset_sort_date_index: Index auf den Sortier-Ausdruck der Galerie

Die Galerie sortiert nach `coalesce(created_at, imported_at)` (`list_assets`,
`assets.py`). `ix_asset_created_at` (Migration 0038) kann das nicht bedienen —
ein Index über die nackte Spalte greift nicht, sobald die Spalte in einem
Ausdruck steckt. SQLite baute deshalb bei jedem Galerie-Request einen
Temp-B-Tree über alle Assets: gemessen 78 ms bei 11.000 Bildern, wachsend.

Mit dem Ausdruck als Index-Key trifft die Query einen Covering Index —
gemessen 0,1 ms auf demselben Datenbestand.

`DESC` steht im Index, weil die Galerie standardmäßig absteigend sortiert;
SQLite liest den Index für `ASC` rückwärts, beide Richtungen sind bedient.

**Das `ANALYZE` am Ende ist nicht optional.** Ohne Tabellen-Statistiken nimmt der
Planer den neuen Index nicht — nachgemessen: Index angelegt, aber weiterhin
Temp-B-Tree und 81 ms; erst nach `ANALYZE` greift er (0,1 ms). Die Datenbanken im
Feld haben bisher gar keine Statistiken (`sqlite_stat1` fehlt komplett), weil nie
ein `ANALYZE` lief. Alle 16 Galerie-Queries wurden vorher/nachher gemessen: keine
einzige wird langsamer, die Facetten „Quelle" und „Bildausschnitt" fallen als
Nebeneffekt von je ~45 ms auf ~5 ms.

Revision ID: 0041
Revises: 0040
Create Date: 2026-07-21
"""
from __future__ import annotations

from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asset_sort_date "
        "ON asset (coalesce(created_at, imported_at) DESC)"
    )
    # Vollständiges ANALYZE, bewusst OHNE `PRAGMA analysis_limit`: mit dem sonst
    # üblichen Limit von 400 bleiben die Schätzungen so grob, dass der Planer beim
    # neuen Index bleibt, wo er war — nachgemessen 100 ms statt 0,1 ms, der Index
    # wäre wirkungslos. Ungebremst dauert der Lauf 0,1 s bei 11.000 Assets.
    op.execute("ANALYZE")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_asset_sort_date")
    # Statistiken neu aufbauen: `DROP INDEX` lässt sonst einen veralteten Eintrag
    # für `ix_asset_sort_date` in `sqlite_stat1` zurück.
    op.execute("ANALYZE")
