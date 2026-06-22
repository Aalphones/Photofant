"""Tests for merge_persons and split_faces — file-count consistency, no data loss."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetInstance, Face, Person
from photofant.media.person_folders import merge_persons, person_folder_name, split_faces

_asset_counter = 0


def _create_person(session: Session, name: str, data_root: Path) -> Person:
    person = Person(name=name, is_unknown=False)
    session.add(person)
    session.flush()
    folder = data_root / person_folder_name(person)
    for sub in ("photos", "favourites", "faces", "edits"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    return person


def _create_asset(session: Session) -> Asset:
    global _asset_counter
    _asset_counter += 1
    asset = Asset(
        content_hash=f"hash_{_asset_counter}",
        source="original",
        width=10,
        height=10,
        file_size=11,
        format="png",
    )
    session.add(asset)
    session.flush()
    return asset


def _create_instance(
    session: Session,
    asset: Asset,
    person: Person,
    data_root: Path,
    *,
    filename: str | None = None,
) -> AssetInstance:
    folder = data_root / person_folder_name(person) / "photos"
    fname = filename or f"asset_{asset.id}.png"
    file_path = folder / fname
    file_path.write_bytes(b"image-bytes")

    instance = AssetInstance(
        asset_id=asset.id,
        person_id=person.id,
        path=str(file_path.resolve()),
    )
    session.add(instance)
    session.flush()
    return instance


def _create_face(
    session: Session,
    asset: Asset,
    person: Person,
    data_root: Path,
    *,
    filename: str | None = None,
) -> Face:
    folder = data_root / person_folder_name(person) / "faces"
    fname = filename or f"face_{asset.id}_{person.id}.jpg"
    crop_path = folder / fname
    crop_path.write_bytes(b"crop-bytes")

    face = Face(
        asset_id=asset.id,
        person_id=person.id,
        crop_path=str(crop_path.resolve()),
        score=0.9,
    )
    session.add(face)
    session.flush()
    return face


# ── merge_persons ──────────────────────────────────────────────────────────


def test_merge_moves_all_files(db_session: Session, tmp_path: Path) -> None:
    person_a = _create_person(db_session, "Alice", tmp_path)
    person_b = _create_person(db_session, "Bob", tmp_path)

    asset1 = _create_asset(db_session)
    asset2 = _create_asset(db_session)

    _create_instance(db_session, asset1, person_a, tmp_path)
    _create_instance(db_session, asset2, person_a, tmp_path)
    _create_face(db_session, asset1, person_a, tmp_path)
    _create_face(db_session, asset2, person_a, tmp_path)

    _create_instance(db_session, _create_asset(db_session), person_b, tmp_path)
    db_session.commit()

    initial_file_count = sum(
        1 for child in tmp_path.rglob("*") if child.is_file()
    )

    result = merge_persons(db_session, person_a.id, person_b.id, tmp_path)
    db_session.commit()

    assert result["faces_moved"] == 2
    assert result["instances_moved"] == 2

    final_file_count = sum(
        1 for child in tmp_path.rglob("*") if child.is_file()
    )
    assert final_file_count == initial_file_count

    assert db_session.get(Person, person_a.id) is None

    remaining_instances = (
        db_session.query(AssetInstance)
        .filter(AssetInstance.person_id == person_b.id, AssetInstance.deleted_at.is_(None))
        .count()
    )
    assert remaining_instances == 3

    remaining_faces = (
        db_session.query(Face).filter(Face.person_id == person_b.id).count()
    )
    assert remaining_faces == 2


def test_merge_deduplicates_shared_asset(db_session: Session, tmp_path: Path) -> None:
    person_a = _create_person(db_session, "Alice", tmp_path)
    person_b = _create_person(db_session, "Bob", tmp_path)

    shared_asset = _create_asset(db_session)
    _create_instance(db_session, shared_asset, person_a, tmp_path, filename="shared.png")
    _create_instance(db_session, shared_asset, person_b, tmp_path, filename="shared.png")
    _create_face(db_session, shared_asset, person_a, tmp_path)
    db_session.commit()

    merge_persons(db_session, person_a.id, person_b.id, tmp_path)
    db_session.commit()

    instances = (
        db_session.query(AssetInstance)
        .filter(
            AssetInstance.asset_id == shared_asset.id,
            AssetInstance.deleted_at.is_(None),
        )
        .all()
    )
    assert len(instances) == 1
    assert instances[0].person_id == person_b.id


def test_merge_source_folder_removed(db_session: Session, tmp_path: Path) -> None:
    person_a = _create_person(db_session, "Alice", tmp_path)
    person_b = _create_person(db_session, "Bob", tmp_path)
    source_folder = person_folder_name(person_a)

    asset = _create_asset(db_session)
    _create_instance(db_session, asset, person_a, tmp_path)
    db_session.commit()

    merge_persons(db_session, person_a.id, person_b.id, tmp_path)
    db_session.commit()

    assert not (tmp_path / source_folder).exists()


# ── split_faces ────────────────────────────────────────────────────────────


def test_split_creates_new_person(db_session: Session, tmp_path: Path) -> None:
    person = _create_person(db_session, "Alice", tmp_path)

    asset1 = _create_asset(db_session)
    asset2 = _create_asset(db_session)

    _create_instance(db_session, asset1, person, tmp_path)
    _create_instance(db_session, asset2, person, tmp_path)

    face1 = _create_face(db_session, asset1, person, tmp_path, filename="face_split1.jpg")
    face2 = _create_face(db_session, asset2, person, tmp_path, filename="face_split2.jpg")
    face3 = _create_face(db_session, asset1, person, tmp_path, filename="face_stay.jpg")
    db_session.commit()

    result = split_faces(db_session, person.id, [face1.id, face2.id], tmp_path)
    db_session.commit()

    assert result["new_person_id"] is not None
    assert result["faces_moved"] == 2

    new_person = db_session.get(Person, result["new_person_id"])
    assert new_person is not None

    db_session.refresh(face1)
    db_session.refresh(face2)
    db_session.refresh(face3)
    assert face1.person_id == new_person.id
    assert face2.person_id == new_person.id
    assert face3.person_id == person.id


def test_split_moves_instance_when_no_faces_remain(db_session: Session, tmp_path: Path) -> None:
    person = _create_person(db_session, "Alice", tmp_path)

    asset = _create_asset(db_session)
    instance = _create_instance(db_session, asset, person, tmp_path)
    face = _create_face(db_session, asset, person, tmp_path)

    keep_asset = _create_asset(db_session)
    _create_instance(db_session, keep_asset, person, tmp_path, filename="keep.png")
    _create_face(db_session, keep_asset, person, tmp_path, filename="keep_face.jpg")
    db_session.commit()

    result = split_faces(db_session, person.id, [face.id], tmp_path)
    db_session.commit()

    new_pid = result["new_person_id"]
    db_session.refresh(instance)
    assert instance.person_id == new_pid

    old_instance = (
        db_session.query(AssetInstance)
        .filter(
            AssetInstance.asset_id == asset.id,
            AssetInstance.person_id == person.id,
            AssetInstance.deleted_at.is_(None),
        )
        .first()
    )
    assert old_instance is None


def test_split_copies_instance_when_faces_remain(db_session: Session, tmp_path: Path) -> None:
    person = _create_person(db_session, "Alice", tmp_path)

    asset = _create_asset(db_session)
    _create_instance(db_session, asset, person, tmp_path)

    face1 = _create_face(db_session, asset, person, tmp_path, filename="face_go.jpg")
    _create_face(db_session, asset, person, tmp_path, filename="face_stay.jpg")
    db_session.commit()

    result = split_faces(db_session, person.id, [face1.id], tmp_path)
    db_session.commit()

    new_pid = result["new_person_id"]

    old_instances = (
        db_session.query(AssetInstance)
        .filter(
            AssetInstance.asset_id == asset.id,
            AssetInstance.person_id == person.id,
            AssetInstance.deleted_at.is_(None),
        )
        .count()
    )
    assert old_instances == 1

    new_instances = (
        db_session.query(AssetInstance)
        .filter(
            AssetInstance.asset_id == asset.id,
            AssetInstance.person_id == new_pid,
            AssetInstance.deleted_at.is_(None),
        )
        .count()
    )
    assert new_instances == 1


def test_split_no_file_loss(db_session: Session, tmp_path: Path) -> None:
    person = _create_person(db_session, "Alice", tmp_path)

    assets = [_create_asset(db_session) for _ in range(3)]
    for idx, asset in enumerate(assets):
        _create_instance(db_session, asset, person, tmp_path, filename=f"asset_{idx}.png")
        _create_face(db_session, asset, person, tmp_path, filename=f"face_{idx}.jpg")
    db_session.commit()

    initial_file_count = sum(1 for child in tmp_path.rglob("*") if child.is_file())

    face_to_split = db_session.query(Face).filter(Face.person_id == person.id).first()
    split_faces(db_session, person.id, [face_to_split.id], tmp_path)
    db_session.commit()

    final_file_count = sum(1 for child in tmp_path.rglob("*") if child.is_file())
    assert final_file_count >= initial_file_count
