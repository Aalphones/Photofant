"""Perceptual hashing (DHash) for duplicate detection."""
from __future__ import annotations

from pathlib import Path

import imagehash
from PIL import Image


def compute_phash(path: Path) -> int:
    """Open image at path, compute 64-bit DHash, return as integer."""
    img = Image.open(path).convert("RGB")
    dhash = imagehash.dhash(img, hash_size=8)
    return int(str(dhash), 16)


def hamming_distance(a: int, b: int) -> int:
    """Count differing bits between two 64-bit hashes."""
    return bin(a ^ b).count("1")
