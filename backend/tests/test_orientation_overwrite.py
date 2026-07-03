from __future__ import annotations

from pathlib import Path

from PIL import Image
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetInstance, Face, Person, ProcessingLedger, Version
from photofant.media import orientation_overwrite as oo


def _patch_cache_path(monkeypatch: object, tmp_path: Path) -> None:
    cache_path = tmp_path / "thumbs.sqlite"
    monkeypatch.setattr(oo, "get_cache_db_path", lambda: cache_path)  # type: ignore[attr-defined]


def _paint_marker(img: Image.Image, corner: tuple[int, int], size: int, color: tuple[int, int, int]) -> None:
    x0, y0 = corner
    for x in range(x0, x0 + size):
        for y in range(y0, y0 + size):
            img.putpixel((x, y), color)


def _make_test_image(path: Path, dims: tuple[int, int] = (40, 20)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", dims, color=(10, 10, 10))
    _paint_marker(img, (dims[0] - 8, 0), 8, (220, 20, 20))  # top-right marker
    img.save(path, format="JPEG", quality=95)


def _seed_person(session: Session, person_id: int, name: str) -> Person:
    person = Person(id=person_id, name=name, is_unknown=False)
    session.add(person)
    session.flush()
    return person


def _seed_asset_instance(
    session: Session,
    data_root: Path,
    person_id: int,
    *,
    content_hash: str,
    filename: str,
    dims: tuple[int, int] = (40, 20),
) -> tuple[Asset, AssetInstance]:
    path = data_root / filename
    _make_test_image(path, dims)
    asset = Asset(
        content_hash=content_hash,
        width=dims[0],
        height=dims[1],
        file_size=path.stat().st_size,
        format="jpeg",
    )
    session.add(asset)
    session.flush()
    instance = AssetInstance(asset_id=asset.id, person_id=person_id, path=str(path))
    session.add(instance)
    session.add(ProcessingLedger(content_hash=content_hash, faces_done=True))
    session.commit()
    return asset, instance


# ── overwrite_version ──────────────────────────────────────────────────────


def test_overwrite_version_rotates_file_and_updates_params(
    db_session: Session, tmp_path: Path, monkeypatch: object,
) -> None:
    _patch_cache_path(monkeypatch, tmp_path)
    person = _seed_person(db_session, 2, "Alex")
    _asset, instance = _seed_asset_instance(
        db_session, tmp_path, person.id, content_hash="h1", filename="orig.jpg",
    )

    version_path = tmp_path / "edit_v1.jpg"
    _make_test_image(version_path)
    version = Version(
        instance_id=instance.id, path=str(version_path), is_current=True,
        params={"width": 40, "height": 20},
    )
    db_session.add(version)
    db_session.commit()

    steps = [{"op": "rotate", "params_dict": {"dir": "cw"}}]
    result = oo.overwrite_version(db_session, version, steps)

    assert result == {"width": 20, "height": 40}
    assert version.params["width"] == 20
    assert version.params["height"] == 40
    with Image.open(version_path) as img:
        assert img.size == (20, 40)


# ── overwrite_face ──────────────────────────────────────────────────────────


def test_overwrite_face_rotates_crop_and_refreshes_resolution_phash(
    db_session: Session, tmp_path: Path, monkeypatch: object,
) -> None:
    _patch_cache_path(monkeypatch, tmp_path)
    person = _seed_person(db_session, 2, "Alex")
    asset, _instance = _seed_asset_instance(
        db_session, tmp_path, person.id, content_hash="h2", filename="orig2.jpg",
    )

    crop_path = tmp_path / "face_1.jpg"
    _make_test_image(crop_path, dims=(20, 20))
    face = Face(
        asset_id=asset.id, person_id=person.id, crop_path=str(crop_path),
        bbox={"x1": 0, "y1": 0, "x2": 20, "y2": 20}, resolution=400, phash="old",
    )
    db_session.add(face)
    db_session.commit()

    old_phash = face.phash
    steps = [{"op": "mirror", "params_dict": {"axis": "h"}}]
    result = oo.overwrite_face(db_session, face, steps)

    assert result == {"width": 20, "height": 20}
    assert face.resolution == 400
    assert face.phash != old_phash


# ── overwrite_instance: single instance ─────────────────────────────────────


def test_overwrite_instance_refreshes_asset_metadata_and_ledger(
    db_session: Session, tmp_path: Path, monkeypatch: object,
) -> None:
    _patch_cache_path(monkeypatch, tmp_path)
    person = _seed_person(db_session, 2, "Alex")
    asset, instance = _seed_asset_instance(
        db_session, tmp_path, person.id, content_hash="h3", filename="orig3.jpg",
    )
    old_hash = asset.content_hash

    steps = [{"op": "rotate", "params_dict": {"dir": "cw"}}]
    result = oo.overwrite_instance(db_session, instance, steps)

    assert result["width"] == 20
    assert result["height"] == 40
    assert asset.width == 20
    assert asset.height == 40
    assert asset.content_hash != old_hash

    with Image.open(instance.path) as img:
        assert img.size == (20, 40)

    assert db_session.get(ProcessingLedger, old_hash) is None
    new_ledger = db_session.get(ProcessingLedger, asset.content_hash)
    assert new_ledger is not None
    assert new_ledger.faces_done is True


def test_overwrite_instance_transforms_bbox_of_every_face_on_the_asset(
    db_session: Session, tmp_path: Path, monkeypatch: object,
) -> None:
    _patch_cache_path(monkeypatch, tmp_path)
    person = _seed_person(db_session, 2, "Alex")
    asset, instance = _seed_asset_instance(
        db_session, tmp_path, person.id, content_hash="h4", filename="orig4.jpg",
    )

    face = Face(
        asset_id=asset.id, person_id=person.id, crop_path=str(tmp_path / "f.jpg"),
        bbox={"x1": 32, "y1": 0, "x2": 40, "y2": 8},  # matches the painted top-right marker
    )
    db_session.add(face)
    db_session.commit()

    steps = [{"op": "rotate", "params_dict": {"dir": "cw"}}]
    oo.overwrite_instance(db_session, instance, steps)
    db_session.refresh(face)

    # cw on a 40x20 image: new_x1=height-y2=20-8=12, new_y1=x1=32, new_x2=height-y1=20, new_y2=x2=40
    assert face.bbox == {"x1": 12, "y1": 32, "x2": 20, "y2": 40}


# ── overwrite_instance: multi-instance (group photo) fan-out ───────────────


def test_overwrite_instance_transforms_every_sibling_instance(
    db_session: Session, tmp_path: Path, monkeypatch: object,
) -> None:
    _patch_cache_path(monkeypatch, tmp_path)
    person_a = _seed_person(db_session, 2, "A")
    person_b = _seed_person(db_session, 3, "B")

    asset, instance_a = _seed_asset_instance(
        db_session, tmp_path, person_a.id, content_hash="h5", filename="a.jpg",
    )
    b_path = tmp_path / "b.jpg"
    _make_test_image(b_path)
    instance_b = AssetInstance(asset_id=asset.id, person_id=person_b.id, path=str(b_path))
    db_session.add(instance_b)
    db_session.commit()

    steps = [{"op": "rotate", "params_dict": {"dir": "cw"}}]
    oo.overwrite_instance(db_session, instance_a, steps)

    with Image.open(instance_a.path) as img_a:
        assert img_a.size == (20, 40)
    with Image.open(instance_b.path) as img_b:
        assert img_b.size == (20, 40)


def test_overwrite_instance_does_not_touch_other_assets_ledger(
    db_session: Session, tmp_path: Path, monkeypatch: object,
) -> None:
    """Rekeying the edited asset's ledger row must not disturb unrelated assets."""
    _patch_cache_path(monkeypatch, tmp_path)
    person = _seed_person(db_session, 2, "Alex")
    _other_asset, _other_instance = _seed_asset_instance(
        db_session, tmp_path, person.id, content_hash="untouched", filename="other.jpg",
    )
    asset, instance = _seed_asset_instance(
        db_session, tmp_path, person.id, content_hash="h6", filename="orig6.jpg",
    )

    steps = [{"op": "mirror", "params_dict": {"axis": "h"}}]
    oo.overwrite_instance(db_session, instance, steps)

    other_ledger = db_session.get(ProcessingLedger, "untouched")
    assert other_ledger is not None
    assert other_ledger.faces_done is True
