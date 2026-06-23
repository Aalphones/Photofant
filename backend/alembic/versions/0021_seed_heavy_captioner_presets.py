"""0021 — seed presets for Qwen2.5-VL (instruct) and JoyCaption (instruct_guided)

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-23

Creates named presets for both heavy captioners. Presets are linked to the
model_registry row if it already exists (user registered the model before
migration ran); otherwise model_id is NULL and they serve as global reference
presets that can be associated later.

Preset names per model:
  Qwen2.5-VL:  "Natürliche Sprache" (default), "Booru-Stil"
  JoyCaption:  "Natürliche Sprache" (default), "Booru-Tag-Liste"
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

_QWEN_MANIFEST_ID = "qwen2-5-vl-7b"
_JOY_MANIFEST_ID = "joycaption-alpha-two"

_QWEN_PRESETS = [
    {
        "name": "Natürliche Sprache",
        "is_default": True,
        "config": {
            "system_prompt": (
                "You are a helpful vision assistant. Describe the image in natural, fluent prose. "
                "Focus on the main subject, composition, colors, and mood."
            ),
            "user_prompt": "Describe this image.",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_new_tokens": 512,
            "repetition_penalty": 1.05,
            "min_pixels": 200704,
            "max_pixels": 1003520,
        },
    },
    {
        "name": "Booru-Stil",
        "is_default": False,
        "config": {
            "system_prompt": (
                "You are a tagging assistant. List image attributes as comma-separated tags in English. "
                "Format: tag1, tag2, tag3. Focus on subject, style, colors, composition, and mood. "
                "Note: output is tag-flavored prose, not a strict Danbooru vocabulary."
            ),
            "user_prompt": "Tag this image.",
            "temperature": 0.3,
            "top_p": 0.9,
            "max_new_tokens": 256,
            "repetition_penalty": 1.1,
            "min_pixels": 200704,
            "max_pixels": 1003520,
        },
    },
]

_JOY_PRESETS = [
    {
        "name": "Natürliche Sprache",
        "is_default": True,
        "config": {
            "caption_type": "Descriptive",
            "caption_length": "medium",
            "extra_options": [],
            "person_name": "",
            "raw_prompt_override": "",
        },
    },
    {
        "name": "Booru-Tag-Liste",
        "is_default": False,
        "config": {
            "caption_type": "Booru Tag List",
            "caption_length": "any",
            "extra_options": [],
            "person_name": "",
            "raw_prompt_override": "",
        },
    },
]


def _get_model_id(conn: sa.engine.Connection, manifest_id: str) -> int | None:
    result = conn.execute(
        sa.text("SELECT id FROM model_registry WHERE manifest_id = :mid"),
        {"mid": manifest_id},
    )
    row = result.fetchone()
    return row[0] if row else None


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(UTC).replace(tzinfo=None)

    qwen_model_id = _get_model_id(conn, _QWEN_MANIFEST_ID)
    joy_model_id = _get_model_id(conn, _JOY_MANIFEST_ID)

    rows = []
    for preset in _QWEN_PRESETS:
        rows.append(
            {
                "name": preset["name"],
                "model_id": qwen_model_id,
                "config": json.dumps(preset["config"]),
                "is_default": 1 if preset["is_default"] else 0,
                "created_at": now,
            }
        )
    for preset in _JOY_PRESETS:
        rows.append(
            {
                "name": preset["name"],
                "model_id": joy_model_id,
                "config": json.dumps(preset["config"]),
                "is_default": 1 if preset["is_default"] else 0,
                "created_at": now,
            }
        )

    for row in rows:
        conn.execute(
            sa.text(
                "INSERT INTO caption_preset (name, model_id, config, is_default, created_at) "
                "VALUES (:name, :model_id, :config, :is_default, :created_at)"
            ),
            row,
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM caption_preset WHERE name IN "
        "('Natürliche Sprache', 'Booru-Stil', 'Booru-Tag-Liste') "
        "AND model_id IS NULL OR model_id IN "
        "(SELECT id FROM model_registry WHERE manifest_id IN "
        "('qwen2-5-vl-7b', 'joycaption-alpha-two'))"
    )
