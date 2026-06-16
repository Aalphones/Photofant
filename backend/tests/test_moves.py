from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from photofant.db.cache import get_thumbnail, init_cache_db, store_thumbnail
from photofant.db.models import Asset, AssetInstance, ProcessingLedger
from photofant.media import moves
from photofant.media.moves import MoveError, _perform_move


def _seed_asset(
    session: Session,
    data_root: Path,
    *,
    content_hash: str = "hash1",
    subfolder: str = "photos",
    name: str = "hash1.png",
) -> tuple[Asset, AssetInstance]:
    target_dir = data_root / "_unknown" / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / name
    file_path.write_bytes(b"image-bytes")

    asset = Asset(
        content_hash=content_hash,
        source="original",
        width=10,
        height=10,
        file_size=len(b"image-bytes"),
        format="png",
    )
    session.add(asset)
    session.flush()

    instance = AssetInstance(asset_id=asset.id, person_id=1, path=str(file_path.resolve()))
    session.add(instance)
    session.add(ProcessingLedger(content_hash=content_hash))
    session.commit()
    return asset, instance


# ── _perform_move: the crash-safe filesystem core ──────────────────────────


def test_perform_move_success(tmp_path: Path) -> None:
    source = tmp_path / "photos" / "a.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"x")
    dest = tmp_path / "favourites" / "a.png"

    result = _perform_move(source, dest)

    assert result == dest
    assert dest.exists()
    assert not source.exists()


def test_perform_move_collision_appends_suffix(tmp_path: Path) -> None:
    source = tmp_path / "photos" / "a.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"new")
    dest = tmp_path / "favourites" / "a.png"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"old")  # genuine collision: different file already there

    result = _perform_move(source, dest)

    assert result == dest.with_name("a_1.png")
    assert result.read_bytes() == b"new"
    assert dest.read_bytes() == b"old"  # untouched


def test_perform_move_recovers_when_source_already_moved(tmp_path: Path) -> None:
    """Simulated crash: a prior move landed the file at dest before the DB commit."""
    source = tmp_path / "photos" / "a.png"  # never created — already gone
    dest = tmp_path / "favourites" / "a.png"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"x")

    result = _perform_move(source, dest)

    assert result == dest
    assert dest.exists()


def test_perform_move_raises_when_file_lost(tmp_path: Path) -> None:
    source = tmp_path / "photos" / "gone.png"
    dest = tmp_path / "favourites" / "gone.png"

    with pytest.raises(MoveError):
        _perform_move(source, dest)


def test_perform_move_noop_when_already_at_dest(tmp_path: Path) -> None:
    path = tmp_path / "photos" / "a.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"x")

    result = _perform_move(path, path)

    assert result == path
    assert path.exists()


# ── set_favourite ───────────────────────────────────────────────────────────


async def test_set_favourite_moves_into_favourites(db_session: Session, tmp_path: Path) -> None:
    _, instance = _seed_asset(db_session, tmp_path)

    await moves.set_favourite(db_session, instance, True)

    moved = Path(instance.path)
    assert instance.favourite is True
    assert moved.parent.name == "favourites"
    assert moved.exists()


async def test_unset_favourite_moves_back_to_photos(db_session: Session, tmp_path: Path) -> None:
    _, instance = _seed_asset(db_session, tmp_path, subfolder="favourites")
    instance.favourite = True
    db_session.commit()

    await moves.set_favourite(db_session, instance, False)

    moved = Path(instance.path)
    assert instance.favourite is False
    assert moved.parent.name == "photos"
    assert moved.exists()


async def test_set_favourite_recovers_after_interrupted_move(db_session: Session, tmp_path: Path) -> None:
    _, instance = _seed_asset(db_session, tmp_path)
    photos_path = Path(instance.path)
    fav_path = photos_path.parent.parent / "favourites" / photos_path.name
    fav_path.parent.mkdir(parents=True, exist_ok=True)
    # Crash simulation: file is already in favourites, DB still points at photos.
    shutil.move(str(photos_path), str(fav_path))

    await moves.set_favourite(db_session, instance, True)

    assert Path(instance.path).resolve() == fav_path.resolve()
    assert instance.favourite is True


# ── soft_delete / restore ───────────────────────────────────────────────────


async def test_soft_delete_moves_to_trash(db_session: Session, tmp_path: Path) -> None:
    _, instance = _seed_asset(db_session, tmp_path)

    await moves.soft_delete(db_session, instance, tmp_path)

    moved = Path(instance.path)
    assert instance.deleted_at is not None
    assert ".photofant" in moved.parts
    assert "trash" in moved.parts
    assert moved.exists()


async def test_restore_round_trips_to_original_location(db_session: Session, tmp_path: Path) -> None:
    _, instance = _seed_asset(db_session, tmp_path)
    original = Path(instance.path).resolve()

    await moves.soft_delete(db_session, instance, tmp_path)
    await moves.restore(db_session, instance, tmp_path)

    assert instance.deleted_at is None
    assert Path(instance.path).resolve() == original
    assert original.exists()


# ── purge ───────────────────────────────────────────────────────────────────


async def test_purge_removes_file_thumbnails_and_rows(db_session: Session, tmp_path: Path) -> None:
    asset, instance = _seed_asset(db_session, tmp_path)
    asset_id = asset.id
    instance_id = instance.id
    content_hash = asset.content_hash
    file_path = Path(instance.path)

    cache_db_path = tmp_path / "thumbnails.sqlite"
    init_cache_db(cache_db_path)
    store_thumbnail(cache_db_path, asset_id, 256, b"thumb")

    await moves.purge(db_session, instance, cache_db_path)

    assert not file_path.exists()
    assert get_thumbnail(cache_db_path, asset_id, 256) is None
    assert db_session.get(Asset, asset_id) is None
    assert db_session.get(AssetInstance, instance_id) is None
    assert db_session.get(ProcessingLedger, content_hash) is None
