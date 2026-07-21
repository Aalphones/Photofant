"""Slug-Erzeugung für backend-seitig (nicht vom User im Wizard) erzeugte Entity-IDs.

Spiegelt exakt die Frontend-Logik (entity-wizard-dialog.ts::slugify, Zeile 278-285) —
gleiche Regel, zwei Sprachen, damit IDs unabhängig vom Entstehungsweg gleich aussehen.
"""
from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", without_diacritics.strip())
    return slug.strip("-")
