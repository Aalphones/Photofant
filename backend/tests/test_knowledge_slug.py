"""slugify (P38 Phase 3) — muss exakt die Frontend-Logik spiegeln
(entity-wizard-dialog.ts::slugify), damit IDs unabhängig vom Entstehungsweg gleich aussehen."""
from __future__ import annotations

from photofant.knowledge.slug import slugify


def test_slugify_lowercases_and_joins_with_dashes() -> None:
    assert slugify("Robert Downey Jr.") == "robert-downey-jr"


def test_slugify_strips_diacritics() -> None:
    assert slugify("Nürtingen") == "nurtingen"


def test_slugify_strips_leading_and_trailing_dashes() -> None:
    assert slugify("  --Iron Man!!--  ") == "iron-man"


def test_slugify_collapses_repeated_separators() -> None:
    assert slugify("A   B---C") == "a-b-c"
