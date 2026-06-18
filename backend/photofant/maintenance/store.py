"""Persistence of the latest reconcile report in the `reconcile_report` table.

The report is a throwaway snapshot, not relational data, so it lives as a single
JSON blob in a singleton table (one row, id = 1). It stays readable until the next
scan overwrites it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from photofant.maintenance.reconcile import ReconcileReport


def persist_report(session: Session, report: ReconcileReport) -> None:
    payload = json.dumps(report.to_dict())
    created_at = datetime.now(UTC).replace(tzinfo=None)
    session.execute(
        text(
            "INSERT INTO reconcile_report (id, payload, created_at) "
            "VALUES (1, :payload, :created_at) "
            "ON CONFLICT(id) DO UPDATE SET "
            "payload = excluded.payload, created_at = excluded.created_at"
        ),
        {"payload": payload, "created_at": created_at},
    )
    session.commit()


def load_report(session: Session) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT payload FROM reconcile_report WHERE id = 1")
    ).fetchone()
    if row is None or row[0] is None:
        return None
    payload: dict[str, Any] = json.loads(row[0])
    return payload
