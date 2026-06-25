"""FS↔DB reconciliation — the data-critical classification core.

Compares the `Data/` filesystem against the active `asset_instance` rows and
sorts every discrepancy into exactly one of three buckets:

- **orphaned** — a file on disk that no active DB row points at (manually added,
  or a moved file whose origin is unknown).
- **missing** — an active DB row whose recorded `path` no longer exists on disk
  *and* whose content was not rediscovered elsewhere.
- **drift** — an active DB row whose `path` is gone, but the *same content*
  (verified by SHA-256, not just by name) was found at a different location.

`classify_reconcile` is deliberately a pure function over plain records so the
classification can be unit-tested in isolation — a wrong call here can cost data
when the user later runs a repair. Drift detection rehashes only size-matched
candidates (the cheap pre-filter), never the whole library.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from photofant.media.meta import compute_hash


@dataclass
class InstanceRecord:
    """One active asset_instance, flattened for classification."""

    instance_id: int
    asset_id: int
    content_hash: str
    file_size: int | None
    path: str
    person_name: str | None


@dataclass
class OrphanItem:
    path: str
    size: int
    person_name: str | None
    detail: str


@dataclass
class MissingItem:
    instance_id: int
    asset_id: int
    path: str
    person_name: str | None
    detail: str


@dataclass
class DriftItem:
    instance_id: int
    asset_id: int
    db_path: str
    found_path: str
    person_name: str | None
    detail: str


@dataclass
class OrphanedFaceItem:
    """A Face DB row whose parent Asset no longer exists."""

    face_id: int
    asset_id: int
    crop_path: str
    person_name: str | None
    detail: str


@dataclass
class AcknowledgedMissingItem:
    """An AssetInstance marked missing (missing_at IS NOT NULL) but not yet purged.

    The reconcile skips these in the main missing-files scan; this bucket makes
    them visible again so the user can finish the cleanup with a purge action.
    """

    instance_id: int
    asset_id: int
    path: str
    person_name: str | None
    missing_at: str
    detail: str


@dataclass
class ReconcileReport:
    generated_at: str
    orphaned_files: list[OrphanItem] = field(default_factory=list)
    missing_files: list[MissingItem] = field(default_factory=list)
    path_drift: list[DriftItem] = field(default_factory=list)
    orphaned_faces: list[OrphanedFaceItem] = field(default_factory=list)
    acknowledged_missing: list[AcknowledgedMissingItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.orphaned_files)
            + len(self.missing_files)
            + len(self.path_drift)
            + len(self.orphaned_faces)
            + len(self.acknowledged_missing)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "orphaned_files": [asdict(item) for item in self.orphaned_files],
            "missing_files": [asdict(item) for item in self.missing_files],
            "path_drift": [asdict(item) for item in self.path_drift],
            "orphaned_faces": [asdict(item) for item in self.orphaned_faces],
            "acknowledged_missing": [asdict(item) for item in self.acknowledged_missing],
        }


def _norm(path: str | Path) -> str:
    """Case- and separator-normalised absolute key for path comparison.

    `resolve()` runs with strict=False, so it also normalises paths whose target
    no longer exists (the missing-file case).
    """
    return os.path.normcase(str(Path(path).resolve()))


def _person_label(person_name: str | None) -> str:
    return person_name if person_name else "_unknown"


def classify_reconcile(
    active: list[InstanceRecord],
    fs_paths: list[Path],
) -> ReconcileReport:
    """Sort the FS/DB discrepancy into orphaned / missing / drift.

    Pure: no DB, no side effects beyond hashing the size-matched drift
    candidates on disk. `fs_paths` is the list of image files found under the
    data root (with the `.photofant/` subtree already excluded by the caller).
    """
    report = ReconcileReport(generated_at=datetime.now(UTC).isoformat())

    fs_by_key: dict[str, Path] = {_norm(path): path for path in fs_paths}

    # Step 1 — split DB rows into "present" (consistent, dropped) and "absent".
    absent: list[InstanceRecord] = []
    for record in active:
        key = _norm(record.path)
        if key in fs_by_key:
            del fs_by_key[key]  # consistent → consumed from the FS pool
        else:
            absent.append(record)

    # Remaining FS files match no active row → orphan candidates.
    orphan_candidates: list[Path] = list(fs_by_key.values())

    # Step 2 — drift: rehash only size-matched orphan candidates against absent rows.
    absent_by_size: dict[int, list[InstanceRecord]] = defaultdict(list)
    for record in absent:
        if record.file_size is not None:
            absent_by_size[record.file_size].append(record)

    consumed_absent: set[int] = set()
    consumed_orphans: set[str] = set()

    for candidate in orphan_candidates:
        try:
            size = candidate.stat().st_size
        except OSError:
            continue
        size_matches = [rec for rec in absent_by_size.get(size, []) if rec.instance_id not in consumed_absent]
        if not size_matches:
            continue

        candidate_hash = compute_hash(candidate)
        for record in size_matches:
            if record.content_hash == candidate_hash:
                report.path_drift.append(
                    DriftItem(
                        instance_id=record.instance_id,
                        asset_id=record.asset_id,
                        db_path=record.path,
                        found_path=str(candidate.resolve()),
                        person_name=record.person_name,
                        detail=f"asset.id={record.asset_id} · {_person_label(record.person_name)}",
                    )
                )
                consumed_absent.add(record.instance_id)
                consumed_orphans.add(_norm(candidate))
                break

    # Step 3 — whatever is left over after drift matching.
    for candidate in orphan_candidates:
        if _norm(candidate) in consumed_orphans:
            continue
        try:
            size = candidate.stat().st_size
        except OSError:
            size = 0
        report.orphaned_files.append(
            OrphanItem(
                path=str(candidate.resolve()),
                size=size,
                person_name=None,
                detail="Keine DB-Eintragszeile",
            )
        )

    for record in absent:
        if record.instance_id in consumed_absent:
            continue
        report.missing_files.append(
            MissingItem(
                instance_id=record.instance_id,
                asset_id=record.asset_id,
                path=record.path,
                person_name=record.person_name,
                detail=f"asset.id={record.asset_id} · {_person_label(record.person_name)}",
            )
        )

    return report
