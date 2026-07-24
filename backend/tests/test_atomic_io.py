from __future__ import annotations

from pathlib import Path

import pytest

from photofant.media.atomic_io import atomic_copy


def _leftover_temp_files(directory: Path) -> list[Path]:
    return [p for p in directory.iterdir() if p.name.endswith(".part")]


def test_copies_content_and_creates_dest(tmp_path: Path) -> None:
    source = tmp_path / "src.jpg"
    source.write_bytes(b"real-image-bytes")
    dest = tmp_path / "person" / "photos" / "dest.jpg"

    result = atomic_copy(source, dest)

    assert result == dest
    assert dest.read_bytes() == b"real-image-bytes"


def test_leaves_no_temp_file_behind_on_success(tmp_path: Path) -> None:
    source = tmp_path / "src.jpg"
    source.write_bytes(b"bytes")
    dest = tmp_path / "photos" / "dest.jpg"

    atomic_copy(source, dest)

    assert _leftover_temp_files(dest.parent) == []


def test_creates_missing_destination_dirs(tmp_path: Path) -> None:
    source = tmp_path / "src.jpg"
    source.write_bytes(b"bytes")
    dest = tmp_path / "a" / "b" / "c" / "dest.jpg"

    atomic_copy(source, dest)

    assert dest.exists()


def test_overwrites_existing_dest_atomically(tmp_path: Path) -> None:
    source = tmp_path / "src.jpg"
    source.write_bytes(b"new-content")
    dest = tmp_path / "dest.jpg"
    dest.write_bytes(b"old-content")

    atomic_copy(source, dest)

    assert dest.read_bytes() == b"new-content"


def test_missing_source_leaves_existing_dest_untouched(tmp_path: Path) -> None:
    """A failed copy must never damage the file already at dest — no half-write."""
    source = tmp_path / "does-not-exist.jpg"
    dest = tmp_path / "dest.jpg"
    dest.write_bytes(b"precious-original")

    with pytest.raises(OSError):
        atomic_copy(source, dest)

    assert dest.read_bytes() == b"precious-original"
    assert _leftover_temp_files(dest.parent) == []
