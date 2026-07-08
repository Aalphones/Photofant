"""0034 — Knowledge-Cache: knowledge_entities/_relationships/_sources/_media_links (P22 Phase 2)

Reiner Cache über der Markdown-Wissensbasis (``photofant/knowledge/vault.py``) — jede Zeile ist
aus dem Vault neu aufbaubar, siehe Kontrakt in
``docs/planning/2026-07-01_p22-knowledge-engine/README.md``. Kind-Tabellen referenzieren
``knowledge_entities.id`` (Format ``<type>/<slug>``); ein DB-seitiges ``ON DELETE CASCADE`` ist
hier bewusst weggelassen — SQLite-FK-Enforcement ist in dieser App nicht aktiviert
(``photofant/db/engine.py`` setzt kein ``PRAGMA foreign_keys=ON``). Das Entfernen der Kind-Zeilen
übernimmt ``EntityRepository.delete`` explizit in Python (gleiches Muster wie
``api/collections.py::delete_collection``).

Revision ID: 0034
Revises: 0033
Create Date: 2026-07-08
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_entities",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status", sa.Text(), nullable=False, server_default=""),
        sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_knowledge_entities_type", "knowledge_entities", ["type"])
    op.create_index("ix_knowledge_entities_domain", "knowledge_entities", ["domain"])

    op.create_table(
        "knowledge_relationships",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_id", sa.Text(), sa.ForeignKey("knowledge_entities.id"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
    )
    op.create_index("ix_knowledge_relationships_entity_id", "knowledge_relationships", ["entity_id"])
    op.create_index("ix_knowledge_relationships_target", "knowledge_relationships", ["target"])

    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_id", sa.Text(), sa.ForeignKey("knowledge_entities.id"), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
    )
    op.create_index("ix_knowledge_sources_entity_id", "knowledge_sources", ["entity_id"])

    op.create_table(
        "knowledge_media_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_id", sa.Text(), sa.ForeignKey("knowledge_entities.id"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),  # person | asset
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("entity_id", "kind", "target_id", name="uq_knowledge_media_link"),
    )
    op.create_index("ix_knowledge_media_links_entity_id", "knowledge_media_links", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_media_links_entity_id", "knowledge_media_links")
    op.drop_table("knowledge_media_links")
    op.drop_index("ix_knowledge_sources_entity_id", "knowledge_sources")
    op.drop_table("knowledge_sources")
    op.drop_index("ix_knowledge_relationships_target", "knowledge_relationships")
    op.drop_index("ix_knowledge_relationships_entity_id", "knowledge_relationships")
    op.drop_table("knowledge_relationships")
    op.drop_index("ix_knowledge_entities_domain", "knowledge_entities")
    op.drop_index("ix_knowledge_entities_type", "knowledge_entities")
    op.drop_table("knowledge_entities")
