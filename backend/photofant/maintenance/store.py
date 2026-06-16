"""Persistence of the latest reconcile report in `app_config`.

The report is a throwaway snapshot, not relational data, so it lives as a single
JSON blob under one `app_config` key rather than in its own table. It stays
readable until the next scan overwrites it.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from photofant.maintenance.reconcile import ReconcileReport

_REPORT_KEY = "reconcile_report"


def persist_report(session: Session, report: ReconcileReport) -> None:
    payload = json.dumps(report.to_dict())
    session.execute(
        text(
            "INSERT INTO app_config (key, value) VALUES (:key, :value) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        ),
        {"key": _REPORT_KEY, "value": payload},
    )
    session.commit()


def load_report(session: Session) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT value FROM app_config WHERE key = :key"),
        {"key": _REPORT_KEY},
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return json.loads(row[0])
