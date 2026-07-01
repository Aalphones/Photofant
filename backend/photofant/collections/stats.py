"""Trainingsset-Statistiken (Konzept §9, P10 Phase 2).

Framing-/Tag-/Qualitäts-Verteilung, AR-Bucket-Verteilung (Kohya-Style) und Near-Dupe-
Quote für ein Trainingsset. Wird live pro Request berechnet — kein persistenter Cache:
bei den hier üblichen Set-Größen (bis niedrige Hunderte) ist der O(n²) pHash-Paarlauf
unter einer Sekunde, eine Cache-Schicht wäre für diese Größenordnung Overengineering.

AR-Buckets orientieren sich an den SDXL/Kohya-Basisauflösungen (512/768/1024²) — jedes
Bild wird der Basis mit der nächstliegenden Pixelzahl zugeordnet, das Seitenverhältnis
auf eine grobe Stufe gerundet (1:1, 4:3, 3:2, 16:9 und deren Hochformat-Pendants).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import func
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetTag, CollectionItem, Tag
from photofant.media.phash import hamming_distance

_BUCKET_BASES = (512, 768, 1024)

# (label, ratio w/h) — geordnet, engste Stufe zuerst geprüft
_AR_STEPS: tuple[tuple[str, float], ...] = (
    ("1:1", 1.0),
    ("4:3", 4 / 3),
    ("3:4", 3 / 4),
    ("3:2", 3 / 2),
    ("2:3", 2 / 3),
    ("16:9", 16 / 9),
    ("9:16", 9 / 16),
)

_NEAR_DUPE_THRESHOLD = 8  # Hamming-Distanz — konsistent mit dupe_scan_job Default


@dataclass
class DistItem:
    value: str
    count: int


@dataclass
class TagFrequency:
    name: str
    count: int


@dataclass
class HistogramBucket:
    label: str
    count: int


@dataclass
class TrainingSetStats:
    total: int
    framing: list[DistItem] = field(default_factory=list)
    tag_frequencies: list[TagFrequency] = field(default_factory=list)
    quality_histogram: list[HistogramBucket] = field(default_factory=list)
    ar_buckets: list[DistItem] = field(default_factory=list)
    near_dupe_rate: float = 0.0


def _nearest_ar_label(width: int, height: int) -> str:
    ratio = width / height
    best_label, best_diff = "1:1", float("inf")
    for label, step_ratio in _AR_STEPS:
        diff = abs(ratio - step_ratio)
        if diff < best_diff:
            best_label, best_diff = label, diff
    return best_label


def _bucket_key(width: int | None, height: int | None) -> str | None:
    if not width or not height:
        return None
    pixels = width * height
    base = min(_BUCKET_BASES, key=lambda candidate: abs(candidate * candidate - pixels))
    return f"{base} · {_nearest_ar_label(width, height)}"


def _quality_bucket_label(index: int) -> str:
    low = index * 20
    high = low + 20
    return f"{low}-{high}%"


def _near_dupe_rate(phashes: list[int]) -> float:
    """Fraction of images that have at least one near-dupe partner in the set."""
    total = len(phashes)
    if total < 2:
        return 0.0
    has_partner = [False] * total
    for i in range(total):
        if has_partner[i]:
            continue
        for j in range(i + 1, total):
            if hamming_distance(phashes[i], phashes[j]) <= _NEAR_DUPE_THRESHOLD:
                has_partner[i] = True
                has_partner[j] = True
    return sum(has_partner) / total


def compute_training_set_stats(session: Session, collection_id: int) -> TrainingSetStats:
    rows = (
        session.query(Asset.id, Asset.framing, Asset.quality_score, Asset.width, Asset.height, Asset.phash)
        .join(CollectionItem, CollectionItem.asset_id == Asset.id)
        .filter(CollectionItem.collection_id == collection_id)
        .all()
    )
    total = len(rows)
    if total == 0:
        return TrainingSetStats(total=0)

    framing_counts = Counter(row.framing for row in rows if row.framing is not None)
    framing = [DistItem(value=value, count=count) for value, count in framing_counts.most_common()]

    quality_buckets = [0] * 5
    for row in rows:
        if row.quality_score is None:
            continue
        index = min(int(row.quality_score * 5), 4)
        quality_buckets[index] += 1
    quality_histogram = [
        HistogramBucket(label=_quality_bucket_label(index), count=count)
        for index, count in enumerate(quality_buckets)
    ]

    bucket_counts = Counter(
        key for key in (_bucket_key(row.width, row.height) for row in rows) if key is not None
    )
    ar_buckets = [DistItem(value=value, count=count) for value, count in bucket_counts.most_common()]

    asset_ids = [row.id for row in rows]
    tag_rows = (
        session.query(Tag.name, func.count(AssetTag.id).label("cnt"))
        .join(AssetTag, AssetTag.tag_id == Tag.id)
        .filter(AssetTag.asset_id.in_(asset_ids), AssetTag.manually_removed.is_(False))
        .group_by(Tag.name)
        .order_by(func.count(AssetTag.id).desc())
        .limit(20)
        .all()
    )
    tag_frequencies = [TagFrequency(name=row.name, count=row.cnt) for row in tag_rows]

    phashes = [row.phash for row in rows if row.phash is not None]
    near_dupe_rate = _near_dupe_rate(phashes)

    return TrainingSetStats(
        total=total,
        framing=framing,
        tag_frequencies=tag_frequencies,
        quality_histogram=quality_histogram,
        ar_buckets=ar_buckets,
        near_dupe_rate=round(near_dupe_rate, 4),
    )
