from __future__ import annotations

from pathlib import Path

import pytest

from photofant.maintenance.reconcile import (
    CORRUPT_EMPTY,
    CORRUPT_SIZE_MISMATCH,
    CORRUPT_UNDECODABLE,
    InstanceRecord,
    assess_file_integrity,
    classify_metadata_gap,
    classify_orphaned_edits,
    classify_reconcile,
    norm_path,
)
from photofant.maintenance.repair import RepairError, ensure_under_root
from photofant.media.meta import compute_hash


def _write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _record(path: Path, *, content_hash: str, file_size: int, instance_id: int = 1) -> InstanceRecord:
    return InstanceRecord(
        instance_id=instance_id,
        asset_id=instance_id,
        content_hash=content_hash,
        file_size=file_size,
        path=str(path),
        person_name="_unknown",
    )


# ── classification: the three buckets + hash-verified drift ──────────────────


def test_consistent_instance_yields_empty_report(tmp_path: Path) -> None:
    photo = _write(tmp_path / "_unknown" / "photos" / "a.png", b"image-a")
    record = _record(photo, content_hash=compute_hash(photo), file_size=photo.stat().st_size)

    report = classify_reconcile([record], [photo])

    assert report.total == 0


def test_orphan_file_without_db_row(tmp_path: Path) -> None:
    orphan = _write(tmp_path / "_unknown" / "photos" / "stranger.png", b"who-am-i")

    report = classify_reconcile([], [orphan])

    assert len(report.orphaned_files) == 1
    assert report.orphaned_files[0].path == str(orphan.resolve())
    assert not report.missing_files
    assert not report.path_drift


def test_missing_when_db_path_gone_and_no_match(tmp_path: Path) -> None:
    gone = tmp_path / "_unknown" / "photos" / "vanished.png"  # never created
    record = _record(gone, content_hash="deadbeef", file_size=123)

    report = classify_reconcile([record], [])

    assert len(report.missing_files) == 1
    assert report.missing_files[0].instance_id == 1
    assert not report.orphaned_files
    assert not report.path_drift


def test_drift_matches_by_content_hash(tmp_path: Path) -> None:
    """File moved to a new spot: same bytes → drift, not orphan+missing."""
    content = b"the-very-same-bytes"
    found = _write(tmp_path / "_unknown" / "photos" / "moved.png", content)
    old_path = tmp_path / "_unknown" / "old" / "moved.png"  # gone
    record = _record(old_path, content_hash=compute_hash(found), file_size=len(content))

    report = classify_reconcile([record], [found])

    assert len(report.path_drift) == 1
    drift = report.path_drift[0]
    assert drift.instance_id == 1
    assert drift.db_path == str(old_path)
    assert drift.found_path == str(found.resolve())
    assert not report.missing_files
    assert not report.orphaned_files


def test_same_size_different_content_is_not_drift(tmp_path: Path) -> None:
    """Size collides but bytes differ → no false drift; stays missing + orphan."""
    orphan = _write(tmp_path / "_unknown" / "photos" / "other.png", b"AAAA")
    gone = tmp_path / "_unknown" / "old" / "real.png"  # gone
    record = _record(gone, content_hash="not-the-orphan-hash", file_size=4)

    report = classify_reconcile([record], [orphan])

    assert len(report.missing_files) == 1
    assert len(report.orphaned_files) == 1
    assert not report.path_drift


def test_size_prefilter_excludes_mismatched_candidate(tmp_path: Path) -> None:
    """A differently-sized orphan is never rehashed against the missing row."""
    orphan = _write(tmp_path / "_unknown" / "photos" / "big.png", b"much-longer-content")
    gone = tmp_path / "_unknown" / "old" / "small.png"
    record = _record(gone, content_hash=compute_hash(orphan), file_size=999_999)

    report = classify_reconcile([record], [orphan])

    # Despite a matching hash, the size pre-filter keeps them apart.
    assert len(report.missing_files) == 1
    assert len(report.orphaned_files) == 1
    assert not report.path_drift


# ── orphaned edits: edits/ files with no matching version.path row ───────────


def test_edit_file_with_version_row_is_not_orphaned(tmp_path: Path) -> None:
    linked = _write(tmp_path / "_unknown" / "edits" / "edit_a.png", b"edited-bytes")

    items = classify_orphaned_edits([linked], {norm_path(linked)})

    assert items == []


def test_edit_file_without_version_row_is_orphaned(tmp_path: Path) -> None:
    unlinked = _write(tmp_path / "_unknown" / "edits" / "edit_b.png", b"edited-bytes")

    items = classify_orphaned_edits([unlinked], set())

    assert len(items) == 1
    assert items[0].path == str(unlinked.resolve())
    assert items[0].detail == "Keine Version-Eintragszeile"


# ── repair path-safety guard (data-critical) ─────────────────────────────────


def test_ensure_under_root_rejects_outside_path(tmp_path: Path) -> None:
    data_root = tmp_path / "Data"
    data_root.mkdir()
    outside = tmp_path / "elsewhere" / "secret.png"

    with pytest.raises(RepairError):
        ensure_under_root(outside, data_root)


def test_ensure_under_root_accepts_inside_path(tmp_path: Path) -> None:
    data_root = tmp_path / "Data"
    inside = data_root / "_unknown" / "photos" / "ok.png"
    inside.parent.mkdir(parents=True)

    resolved = ensure_under_root(inside, data_root)

    assert str(resolved).startswith(str(data_root.resolve()))


# ── integrity assessment: the "present but broken" decision (data-critical) ──


def test_zero_bytes_is_empty_regardless_of_expected() -> None:
    assert assess_file_integrity(0, expected_size=1234, decodable=None) == CORRUPT_EMPTY
    assert assess_file_integrity(0, expected_size=None, decodable=True) == CORRUPT_EMPTY


def test_size_mismatch_flags_half_written_copy() -> None:
    # The move was interrupted: only part of the file made it to the new path.
    assert assess_file_integrity(500, expected_size=1234, decodable=None) == CORRUPT_SIZE_MISMATCH


def test_size_match_is_trusted_without_decoding() -> None:
    # Bytes on disk match what we recorded at import → intact, no decode probe needed.
    assert assess_file_integrity(1234, expected_size=1234, decodable=None) is None


def test_unknown_size_falls_back_to_decode_probe() -> None:
    # Older asset without a recorded size: the decode probe is the only signal.
    assert assess_file_integrity(999, expected_size=None, decodable=False) == CORRUPT_UNDECODABLE
    assert assess_file_integrity(999, expected_size=None, decodable=True) is None


def test_unknown_size_and_no_probe_result_is_treated_as_intact() -> None:
    # decodable=None with no reference size → nothing to accuse the file of.
    assert assess_file_integrity(999, expected_size=None, decodable=None) is None


# ── metadata gap: reprocessable vs blocked (the "fixed it, it comes back" fix) ──


def _flags(tags: bool, caption: bool, embedding: bool) -> dict[str, bool]:
    return {"tags": tags, "caption": caption, "embedding": embedding}


def test_wanted_available_and_undone_is_reprocessable() -> None:
    # Enabled, a model is active, not done yet → the Nachziehen button will do something.
    missing, blocked = classify_metadata_gap(
        wanted=_flags(True, True, True),
        available=_flags(True, True, True),
        done=_flags(False, False, False),
    )
    assert missing == ["tags", "caption", "embedding"]
    assert blocked == []


def test_wanted_but_no_model_is_blocked_not_reprocessable() -> None:
    # This is the zombie: on in settings, no model → it must NOT be offered as a reprocess row.
    missing, blocked = classify_metadata_gap(
        wanted=_flags(True, True, True),
        available=_flags(False, False, False),
        done=_flags(False, False, False),
    )
    assert missing == []
    assert blocked == ["tags", "caption", "embedding"]


def test_done_steps_are_neither_missing_nor_blocked() -> None:
    missing, blocked = classify_metadata_gap(
        wanted=_flags(True, True, True),
        available=_flags(True, True, True),
        done=_flags(True, True, True),
    )
    assert missing == []
    assert blocked == []


def test_disabled_step_is_ignored_even_without_a_model() -> None:
    # auto_caption off → not a gap at all, regardless of model availability.
    missing, blocked = classify_metadata_gap(
        wanted=_flags(True, False, True),
        available=_flags(True, False, True),
        done=_flags(False, False, False),
    )
    assert missing == ["tags", "embedding"]
    assert blocked == []


def test_mixed_availability_splits_per_step() -> None:
    # tags has a model (reprocessable), embedding is on but modelless (blocked), caption done.
    missing, blocked = classify_metadata_gap(
        wanted=_flags(True, True, True),
        available=_flags(True, True, False),
        done=_flags(False, True, False),
    )
    assert missing == ["tags"]
    assert blocked == ["embedding"]
