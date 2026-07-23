"""0042 — collection_item: face_id als Alternative zu asset_id (XOR)

Trainingssets sollen Face-Crops als eigenständige Mitglieder aufnehmen können, nicht nur ganze
Fotos (P-Gesichter-Mehrfachauswahl, ADR-035). asset_id wird nullable, eine neue face_id-Spalte
kommt dazu (FK auf face.id), CheckConstraint erzwingt XOR wie beim Version-Modell (0018).

Der bisherige zusammengesetzte PK (collection_id, asset_id) kann nicht bestehen bleiben, sobald
asset_id nullable wird (mehrere Face-Items mit asset_id=NULL in derselben Collection wären sonst
nicht mehr über den PK unterscheidbar) — Umstieg auf einen surrogaten Integer-PK `id`, Uniqueness
pro Achse über zwei partielle Unique-Indizes (Muster aus 0027: ein normaler Multi-Spalten-Unique-
Constraint greift bei NULL-Werten laut SQL-Standard nicht).

Umsetzung als manueller Tabellen-Neuaufbau (create new → INSERT SELECT → drop old → rename) statt
`batch_alter_table(recreate="always")` mit `drop_constraint(type_="primary")`: SQLite speichert den
PK-Constraint-Namen nicht, der reflektierte PK heißt also nicht `pk_collection_item` — ein Drop per
Name wäre unzuverlässig. Keine andere Tabelle referenziert `collection_item` per FK, drop+rename ist
daher gefahrlos. Idempotent über einen Spalten-Guard (re-run-sicher, python.md).

Revision ID: 0042
Revises: 0041
Create Date: 2026-07-23
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_index(table: str, index: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return False
    return index in {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    # Idempotenz-Guard: face_id schon da → Migration bereits gelaufen, nichts tun (python.md).
    if _has_column("collection_item", "face_id"):
        return

    # Zielschema unter temporärem Namen aufbauen. asset_id wird nullable, face_id kommt dazu,
    # surrogater id-PK ersetzt den zusammengesetzten PK.
    op.create_table(
        "collection_item_new",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("collection.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=True),
        sa.Column("face_id", sa.Integer(), sa.ForeignKey("face.id"), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("caption_override", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(asset_id IS NOT NULL AND face_id IS NULL) OR (asset_id IS NULL AND face_id IS NOT NULL)",
            name="ck_collection_item_xor",
        ),
    )
    # Bestandsdaten übernehmen — surrogate id vergibt SQLite selbst (kein FK referenziert den PK).
    op.execute(
        "INSERT INTO collection_item_new "
        "(collection_id, asset_id, source, caption_override, position) "
        "SELECT collection_id, asset_id, source, caption_override, position FROM collection_item"
    )
    op.drop_table("collection_item")
    op.rename_table("collection_item_new", "collection_item")

    # Uniqueness pro Achse über partielle Indizes (0027-Muster): ein normaler Multi-Spalten-
    # Unique-Constraint greift bei NULL-Werten laut SQL-Standard nicht.
    op.create_index(
        "uq_collection_item_asset", "collection_item", ["collection_id", "asset_id"],
        unique=True, sqlite_where=sa.text("asset_id IS NOT NULL"),
    )
    op.create_index(
        "uq_collection_item_face", "collection_item", ["collection_id", "face_id"],
        unique=True, sqlite_where=sa.text("face_id IS NOT NULL"),
    )
    # Plain-Indizes passend zu den index=True-Deklarationen im Model.
    op.create_index("ix_collection_item_collection_id", "collection_item", ["collection_id"])
    op.create_index("ix_collection_item_asset_id", "collection_item", ["asset_id"])
    op.create_index("ix_collection_item_face_id", "collection_item", ["face_id"])


def downgrade() -> None:
    # Idempotenz-Guard: face_id schon weg → bereits heruntermigriert.
    if not _has_column("collection_item", "face_id"):
        return

    # Face-Items können nicht zurück in ein asset_id-only-Schema — sie müssen vor dem Downgrade
    # gelöscht sein, sonst verletzt der alte NOT-NULL-Constraint auf asset_id die Restdaten.
    op.execute("DELETE FROM collection_item WHERE face_id IS NOT NULL")

    for index in (
        "ix_collection_item_face_id",
        "ix_collection_item_asset_id",
        "ix_collection_item_collection_id",
        "uq_collection_item_face",
        "uq_collection_item_asset",
    ):
        if _has_index("collection_item", index):
            op.drop_index(index, table_name="collection_item")

    op.create_table(
        "collection_item_old",
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("collection.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id"), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("caption_override", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("collection_id", "asset_id", name="pk_collection_item"),
    )
    op.execute(
        "INSERT INTO collection_item_old "
        "(collection_id, asset_id, source, caption_override, position) "
        "SELECT collection_id, asset_id, source, caption_override, position FROM collection_item"
    )
    op.drop_table("collection_item")
    op.rename_table("collection_item_old", "collection_item")
    op.create_index("ix_collection_item_asset_id", "collection_item", ["asset_id"])
