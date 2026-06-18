"""0013 — app_config abschaffen: Werte nach settings.json, Reconcile-Report in eigene Tabelle

Migriert die letzten Live-Werte aus `app_config` in die settings.json (nur Keys, die
dort noch fehlen — bestehende settings.json-Werte gewinnen), zieht den Reconcile-Report
in die neue Tabelle `reconcile_report` um und droppt `app_config`.

Die settings.json-Schreiberei ist ein Dateizugriff außerhalb der DB-Transaktion und
idempotent (nur fehlende Keys), darum bei einem Re-Run ungefährlich.

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-18
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

# app_config-Keys, die in die settings.json wandern (String-encoded → echte JSON-Typen).
_STRING_KEYS = ("data_root", "models_dir")
_FLOAT_KEYS = ("tagging_threshold",)
_RECONCILE_KEY = "reconcile_report"


def upgrade() -> None:
    bind = op.get_bind()
    config = _read_app_config(bind)

    _migrate_values_to_settings(config)

    op.create_table(
        "reconcile_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("id = 1", name="reconcile_report_singleton"),
    )

    reconcile_blob = config.get(_RECONCILE_KEY)
    if reconcile_blob:
        bind.execute(
            sa.text(
                "INSERT INTO reconcile_report (id, payload, created_at) "
                "VALUES (1, :payload, :created_at)"
            ),
            {"payload": reconcile_blob, "created_at": datetime.now(UTC).replace(tzinfo=None)},
        )

    op.drop_table("app_config")


def downgrade() -> None:
    # Best-effort: app_config-Tabelle wiederherstellen und Reconcile-Report zurückschreiben.
    # Die settings.json bleibt unangetastet (kein zuverlässiger Rückkanal pro Key).
    bind = op.get_bind()

    op.create_table(
        "app_config",
        sa.Column("key", sa.Text(), nullable=False, primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
    )

    reconcile_row = bind.execute(
        sa.text("SELECT payload FROM reconcile_report WHERE id = 1")
    ).fetchone()
    if reconcile_row is not None and reconcile_row[0] is not None:
        bind.execute(
            sa.text("INSERT INTO app_config (key, value) VALUES (:key, :value)"),
            {"key": _RECONCILE_KEY, "value": reconcile_row[0]},
        )

    op.drop_table("reconcile_report")


def _read_app_config(bind: sa.engine.Connection) -> dict[str, str]:
    rows = bind.execute(sa.text("SELECT key, value FROM app_config")).fetchall()
    return {key: value for key, value in rows if value is not None}


def _migrate_values_to_settings(config: dict[str, str]) -> None:
    """Merge known app_config values into settings.json — only keys not already present."""
    from photofant.settings import get_settings_path

    path = get_settings_path()
    raw: dict[str, object] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = {}

    changed = False
    for key in _STRING_KEYS:
        if key in config and key not in raw:
            raw[key] = config[key]
            changed = True
    for key in _FLOAT_KEYS:
        if key in config and key not in raw:
            try:
                raw[key] = float(config[key])
                changed = True
            except (TypeError, ValueError):
                pass

    if not changed:
        return

    raw.setdefault("_schema_version", 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / (path.name + ".tmp")
    tmp_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.rename(path)
