"""Perceptual hashing (DHash) for duplicate detection."""
from __future__ import annotations

from pathlib import Path

import imagehash
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session


def compute_phash(path: Path) -> int:
    """Open image at path, compute 64-bit DHash, return as signed int64."""
    img = Image.open(path).convert("RGB")
    dhash = imagehash.dhash(img, hash_size=8)
    value = int(str(dhash), 16)
    # SQLite stores signed int64 only — wrap values with the high bit set
    if value >= 2**63:
        value -= 2**64
    return value


def compute_phash_hex(path: Path) -> str:
    """Open image at path, compute 64-bit DHash, return as hex string (Face.phash format)."""
    img = Image.open(path).convert("RGB")
    return str(imagehash.dhash(img, hash_size=8))


def hamming_distance(a: int, b: int) -> int:
    """Count differing bits between two 64-bit hashes."""
    return bin(a ^ b).count("1")


def find_similar(
    session: Session,
    new_phash: int,
    new_asset_id: int,
    threshold: int,
) -> list[tuple[int, int]]:
    """Return (asset_id, distance) pairs for all assets within threshold of new_phash.

    Results are sorted by distance ascending (closest match first).
    """
    from photofant.db.models import Asset

    rows = session.execute(
        select(Asset.id, Asset.phash).where(
            Asset.phash.is_not(None),
            Asset.id != new_asset_id,
        )
    ).all()

    matches: list[tuple[int, int]] = []
    for asset_id, asset_phash in rows:
        distance = hamming_distance(new_phash, asset_phash)
        if distance <= threshold:
            matches.append((asset_id, distance))

    return sorted(matches, key=lambda pair: pair[1])
