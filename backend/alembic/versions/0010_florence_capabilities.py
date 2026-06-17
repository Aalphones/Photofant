"""0010 — backfill capabilities descriptor for Florence-2-base registry rows

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-17

Fills model_registry.capabilities for any existing florence-2-base row that
was registered before Phase 6. New registrations get capabilities from the
manifest via _upsert_registry_row (download_job.py / register-local).
"""
from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_FLORENCE_CAPABILITIES: dict = {
    "info": (
        "Florence-2 folgt keinen freien Anweisungen und kennt kein Temperatur-Sampling "
        "(deterministische Beam-Search). Stil und Länge steuerst du ausschließlich über das "
        "Task-Token — es gibt hier bewusst kein System-Prompt-Feld."
    ),
    "fields": [
        {
            "key": "task_token",
            "type": "dropdown",
            "label": "Task-Token",
            "desc": "Steuert die Ausführlichkeit: kurz = ein Satz, detailliert = mehrere Sätze, ausführlich = Absatz.",
            "default": "<DETAILED_CAPTION>",
            "options": [
                {"value": "<CAPTION>", "label": "Kurz (ein Satz)"},
                {"value": "<DETAILED_CAPTION>", "label": "Detailliert (mehrere Sätze)"},
                {"value": "<MORE_DETAILED_CAPTION>", "label": "Ausführlich (Absatz)"},
            ],
        },
        {
            "key": "max_new_tokens",
            "type": "number",
            "label": "max_new_tokens",
            "desc": "Obergrenze der Ausgabelänge.",
            "default": 1024,
            "min": 1,
            "max": 4096,
        },
        {
            "key": "num_beams",
            "type": "number",
            "label": "num_beams",
            "desc": "Beam-Search-Breite. Höher = tendenziell bessere, aber langsamere Ergebnisse.",
            "default": 3,
            "min": 1,
            "max": 16,
        },
    ],
}


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE model_registry SET capabilities = :caps "
            "WHERE manifest_id = 'florence-2-base' AND capabilities IS NULL"
        ).bindparams(caps=json.dumps(_FLORENCE_CAPABILITIES))
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE model_registry SET capabilities = NULL "
            "WHERE manifest_id = 'florence-2-base'"
        )
    )
