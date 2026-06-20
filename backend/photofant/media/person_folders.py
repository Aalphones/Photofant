"""Person-folder orchestration — physical folders, moves/copies for person assignments.

After clustering or manual assignment, this module creates person directories,
moves the _unknown instance to the first person, and creates copies for
additional persons. All filesystem operations are crash-safe: a crash between
move and DB commit leaves forward-recoverable drift (detected by reconcile).

Folder convention:
  _unknown/    → catch-all person (person.is_unknown)
  person_{id}/ → named persons
  Each has subfolders: photos/ favourites/ faces/ edits/
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from photofant.db.models import AssetInstance, Face, Person

log = logging.getLogger(__name__)

_PERSON_SUBFOLDERS = ["photos", "favourites", "faces", "edits"]


def person_folder_name(person: Person) -> str:
    if person.is_unknown:
        return "_unknown"
    return f"person_{person.id}"


def ensure_person_folder(data_root: Path, person: Person) -> Path:
    folder = data_root / person_folder_name(person)
    for sub in _PERSON_SUBFOLDERS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    return folder


def person_id_from_path(file_path: Path, data_root: Path) -> int | None:
    """Extract person DB id from a file path inside a person_{id}/ folder.

    Returns None for _unknown/ or paths outside person folders.
    """
    try:
        relative = file_path.resolve().relative_to(data_root.resolve())
    except ValueError:
        return None

    parts = relative.parts
    if len(parts) < 2:
        return None

    folder = parts[0]
    if folder.startswith("person_"):
        try:
            return int(folder[7:])
        except ValueError:
            return None
    return None


def is_importable_person_subfolder(file_path: Path, data_root: Path) -> bool:
    """True if the file sits in a person folder's photos/ or favourites/ dir."""
    try:
        relative = file_path.resolve().relative_to(data_root.resolve())
    except ValueError:
        return False

    parts = relative.parts
    if len(parts) < 3:
        return False

    return parts[0].startswith("person_") and parts[1] in ("photos", "favourites")


# ── crash-safe file helpers ──────────────────────────────────────────────


def _resolve_collision(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    counter = 1
    candidate = dest.with_name(f"{stem}_{counter}{suffix}")
    while candidate.exists():
        counter += 1
        candidate = dest.with_name(f"{stem}_{counter}{suffix}")
    return candidate


def _safe_move(source: Path, dest: Path) -> Path:
    """Move with crash recovery: source gone + dest present → adopt dest."""
    if source.resolve() == dest.resolve():
        if dest.exists():
            return dest
        raise FileNotFoundError(f"File missing at recorded path: {source}")

    if not source.exists():
        if dest.exists():
            log.warning("Source %s gone but %s present — adopting (interrupted move)", source, dest)
            return dest
        raise FileNotFoundError(f"Source missing and no destination: {source}")

    final = _resolve_collision(dest)
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(final))
    return final


def _safe_copy(source: Path, dest: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Source file missing for copy: {source}")
    final = _resolve_collision(dest)
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(final))
    return final


# ── instance materialization ─────────────────────────────────────────────


def materialize_assignment(
    session: Session,
    asset_id: int,
    target_person_id: int,
    data_root: Path,
    *,
    fixed: bool = False,
) -> AssetInstance | None:
    """Ensure an asset has a physical instance in the target person's folder.

    Move-vs-copy rules:
      - _unknown instance exists, is not fixed, no other real-person instance
        yet → MOVE (_unknown instance row is reused).
      - Otherwise → COPY from any existing instance.

    Returns the instance or None on failure.
    """
    person = session.get(Person, target_person_id)
    if person is None:
        log.error("Person %d not found", target_person_id)
        return None

    existing = session.scalar(
        select(AssetInstance).where(
            AssetInstance.asset_id == asset_id,
            AssetInstance.person_id == target_person_id,
            AssetInstance.deleted_at.is_(None),
        )
    )
    if existing is not None:
        if fixed and not existing.fixed_person:
            existing.fixed_person = True
        return existing

    person_dir = ensure_person_folder(data_root, person)

    unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
    unknown_instance: AssetInstance | None = None
    if unknown_person:
        unknown_instance = session.scalar(
            select(AssetInstance).where(
                AssetInstance.asset_id == asset_id,
                AssetInstance.person_id == unknown_person.id,
                AssetInstance.deleted_at.is_(None),
            )
        )

    real_instance_count: int = session.scalar(
        select(func.count())
        .select_from(AssetInstance)
        .where(
            AssetInstance.asset_id == asset_id,
            AssetInstance.deleted_at.is_(None),
            AssetInstance.person_id != (unknown_person.id if unknown_person else -1),
        )
    ) or 0

    can_move_unknown = (
        unknown_instance is not None
        and not unknown_instance.fixed_person
        and real_instance_count == 0
    )

    if can_move_unknown:
        source_path = Path(unknown_instance.path)
        subfolder = "favourites" if unknown_instance.favourite else "photos"
        dest = person_dir / subfolder / source_path.name

        try:
            final = _safe_move(source_path, dest)
        except FileNotFoundError:
            log.error("Cannot move _unknown instance for asset %d — file missing", asset_id)
            return None

        unknown_instance.person_id = target_person_id
        unknown_instance.path = str(final.resolve())
        if fixed:
            unknown_instance.fixed_person = True
        session.flush()
        log.info("Moved asset %d from _unknown to person %d", asset_id, target_person_id)
        return unknown_instance
    else:
        source_instance = session.scalar(
            select(AssetInstance)
            .where(AssetInstance.asset_id == asset_id, AssetInstance.deleted_at.is_(None))
            .order_by(AssetInstance.favourite.asc())
            .limit(1)
        )
        if source_instance is None:
            log.error("No source instance for asset %d to copy from", asset_id)
            return None

        source_path = Path(source_instance.path)
        dest = person_dir / "photos" / source_path.name

        try:
            final = _safe_copy(source_path, dest)
        except FileNotFoundError:
            log.error("Cannot copy for asset %d — source missing: %s", asset_id, source_path)
            return None

        new_instance = AssetInstance(
            asset_id=asset_id,
            person_id=target_person_id,
            path=str(final.resolve()),
            fixed_person=fixed,
        )
        session.add(new_instance)
        session.flush()
        log.info("Copied asset %d to person %d", asset_id, target_person_id)
        return new_instance


def move_face_crops_to_person(
    session: Session,
    asset_id: int,
    person_id: int,
    data_root: Path,
) -> int:
    """Move face crops for (asset, person) to the person's faces/ dir.

    Returns the number of crops moved.
    """
    person = session.get(Person, person_id)
    if person is None:
        return 0

    person_dir = ensure_person_folder(data_root, person)
    faces_dir = person_dir / "faces"
    moved = 0

    faces = session.scalars(
        select(Face).where(Face.asset_id == asset_id, Face.person_id == person_id)
    ).all()

    for face in faces:
        old_path = Path(face.crop_path)
        new_path = faces_dir / old_path.name
        if old_path.resolve() == new_path.resolve():
            continue
        try:
            final = _safe_move(old_path, new_path)
            face.crop_path = str(final.resolve())
            moved += 1
        except FileNotFoundError:
            log.warning("Face crop %s missing — skipping move for face %d", old_path, face.id)

    session.flush()
    return moved


# ── bulk post-clustering materialization ─────────────────────────────────


def materialize_clustering_results(
    session: Session,
    data_root: Path,
) -> dict[str, int]:
    """After clustering, create folders and move/copy files for all new assignments.

    Processes every (asset, person) pair where a face is assigned to a
    real person but no asset_instance exists yet.

    Returns stats: {instances_created, crops_moved}.
    """
    unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
    if unknown_person is None:
        return {"instances_created": 0, "crops_moved": 0}

    pairs = session.execute(
        select(Face.asset_id, Face.person_id)
        .where(
            Face.person_id != unknown_person.id,
            Face.person_id.isnot(None),
            Face.asset_id.isnot(None),
        )
        .distinct()
    ).fetchall()

    if not pairs:
        return {"instances_created": 0, "crops_moved": 0}

    instances_created = 0
    crops_moved = 0

    for asset_id_raw, person_id_raw in pairs:
        asset_id = int(asset_id_raw)
        person_id = int(person_id_raw)

        instance = materialize_assignment(session, asset_id, person_id, data_root)
        if instance is not None:
            instances_created += 1

        crops_moved += move_face_crops_to_person(session, asset_id, person_id, data_root)

    session.commit()
    log.info(
        "Materialization done: %d instances created, %d crops moved",
        instances_created, crops_moved,
    )
    return {"instances_created": instances_created, "crops_moved": crops_moved}


# ── manual face reassignment ────────────────────────────────────────────


def reassign_face(
    session: Session,
    face_id: int,
    new_person_id: int,
    data_root: Path,
) -> dict[str, int | None]:
    """Reassign a face to a different person with physical moves.

    Steps:
      1. Update face.person_id
      2. Move face crop to new person's faces/ dir
      3. Ensure asset instance in new person's folder (fixed_person=True)
      4. If old person has no more faces for this asset, remove their instance

    Returns {face_id, old_person_id, new_person_id, asset_id}.
    """
    face = session.get(Face, face_id)
    if face is None:
        raise ValueError(f"Face {face_id} not found")

    old_person_id = face.person_id
    asset_id = face.asset_id

    if old_person_id == new_person_id:
        return {
            "face_id": face_id,
            "old_person_id": old_person_id,
            "new_person_id": new_person_id,
            "asset_id": asset_id,
        }

    new_person = session.get(Person, new_person_id)
    if new_person is None:
        raise ValueError(f"Person {new_person_id} not found")

    face.person_id = new_person_id

    new_person_dir = ensure_person_folder(data_root, new_person)
    old_crop = Path(face.crop_path)
    new_crop = new_person_dir / "faces" / old_crop.name
    try:
        final = _safe_move(old_crop, new_crop)
        face.crop_path = str(final.resolve())
    except FileNotFoundError:
        log.warning("Face crop %s missing during reassign — path not updated", old_crop)

    materialize_assignment(session, asset_id, new_person_id, data_root, fixed=True)

    if old_person_id is not None:
        remaining_faces: int = session.scalar(
            select(func.count())
            .select_from(Face)
            .where(Face.asset_id == asset_id, Face.person_id == old_person_id)
        ) or 0

        if remaining_faces == 0:
            old_instance = session.scalar(
                select(AssetInstance).where(
                    AssetInstance.asset_id == asset_id,
                    AssetInstance.person_id == old_person_id,
                    AssetInstance.deleted_at.is_(None),
                )
            )
            if old_instance and not old_instance.fixed_person:
                old_path = Path(old_instance.path)
                if old_path.exists():
                    old_path.unlink()
                    log.info("Removed orphaned instance file %s", old_path)
                session.delete(old_instance)

    session.flush()
    log.info(
        "Reassigned face %d: person %s → %d (asset %d)",
        face_id, old_person_id, new_person_id, asset_id,
    )
    return {
        "face_id": face_id,
        "old_person_id": old_person_id,
        "new_person_id": new_person_id,
        "asset_id": asset_id,
    }


# ── merge two persons ─────────────────────────────────────────────────


def merge_persons(
    session: Session,
    from_person_id: int,
    into_person_id: int,
    data_root: Path,
) -> dict[str, int]:
    """Merge from_person into into_person: move all assets and faces.

    Steps:
      1. Reassign all faces from source to target
      2. Move all asset instances (files) to target person folder
      3. Delete the source person row

    Returns {faces_moved, instances_moved}.
    """
    from_person = session.get(Person, from_person_id)
    into_person = session.get(Person, into_person_id)
    if from_person is None:
        raise ValueError(f"Source person {from_person_id} not found")
    if into_person is None:
        raise ValueError(f"Target person {into_person_id} not found")

    into_dir = ensure_person_folder(data_root, into_person)

    faces = session.scalars(
        select(Face).where(Face.person_id == from_person_id)
    ).all()
    faces_moved = 0
    for face in faces:
        face.person_id = into_person_id
        old_crop = Path(face.crop_path)
        new_crop = into_dir / "faces" / old_crop.name
        try:
            final = _safe_move(old_crop, new_crop)
            face.crop_path = str(final.resolve())
        except FileNotFoundError:
            log.warning("Face crop %s missing during merge — skipping", old_crop)
        faces_moved += 1
    session.flush()

    instances = session.scalars(
        select(AssetInstance).where(
            AssetInstance.person_id == from_person_id,
            AssetInstance.deleted_at.is_(None),
        )
    ).all()

    instances_moved = 0
    for instance in instances:
        existing_target = session.scalar(
            select(AssetInstance).where(
                AssetInstance.asset_id == instance.asset_id,
                AssetInstance.person_id == into_person_id,
                AssetInstance.deleted_at.is_(None),
            )
        )

        if existing_target is not None:
            old_path = Path(instance.path)
            if old_path.exists():
                old_path.unlink()
            session.delete(instance)
            instances_moved += 1
            continue

        subfolder = "favourites" if instance.favourite else "photos"
        old_path = Path(instance.path)
        new_path = into_dir / subfolder / old_path.name
        try:
            final = _safe_move(old_path, new_path)
            instance.person_id = into_person_id
            instance.path = str(final.resolve())
            instances_moved += 1
        except FileNotFoundError:
            log.warning("Instance file %s missing during merge — skipping", old_path)

    session.flush()

    remaining = session.scalar(
        select(func.count()).select_from(AssetInstance).where(
            AssetInstance.person_id == from_person_id,
            AssetInstance.deleted_at.is_(None),
        )
    ) or 0

    if remaining == 0 and not from_person.is_unknown:
        from_dir = data_root / person_folder_name(from_person)
        session.delete(from_person)
        session.flush()
        if from_dir.exists():
            import shutil as _shutil
            _shutil.rmtree(str(from_dir), ignore_errors=True)
            log.info("Removed empty person folder %s", from_dir)

    log.info(
        "Merged person %d into %d: %d faces, %d instances moved",
        from_person_id, into_person_id, faces_moved, instances_moved,
    )
    return {"faces_moved": faces_moved, "instances_moved": instances_moved}


# ── split faces into new person ────────────────────────────────────────


def split_faces(
    session: Session,
    source_person_id: int,
    face_ids: list[int],
    data_root: Path,
) -> dict[str, int | None]:
    """Split selected faces from a person into a new person.

    Creates a new Person, reassigns the given faces, and materializes
    the new person folder with the affected asset instances.

    Returns {new_person_id, faces_moved, instances_created}.
    """
    source_person = session.get(Person, source_person_id)
    if source_person is None:
        raise ValueError(f"Source person {source_person_id} not found")

    new_person = Person(name=None, is_unknown=False)
    session.add(new_person)
    session.flush()

    new_dir = ensure_person_folder(data_root, new_person)
    faces_moved = 0

    for fid in face_ids:
        face = session.get(Face, fid)
        if face is None or face.person_id != source_person_id:
            continue

        face.person_id = new_person.id
        old_crop = Path(face.crop_path)
        new_crop = new_dir / "faces" / old_crop.name
        try:
            final = _safe_move(old_crop, new_crop)
            face.crop_path = str(final.resolve())
        except FileNotFoundError:
            log.warning("Face crop %s missing during split — skipping move", old_crop)
        faces_moved += 1

    session.flush()

    affected_assets = session.execute(
        select(Face.asset_id)
        .where(Face.id.in_(face_ids), Face.asset_id.isnot(None))
        .distinct()
    ).fetchall()

    instances_created = 0
    for (asset_id_raw,) in affected_assets:
        asset_id = int(asset_id_raw)

        still_in_source = session.scalar(
            select(func.count()).select_from(Face).where(
                Face.asset_id == asset_id,
                Face.person_id == source_person_id,
            )
        ) or 0

        if still_in_source == 0:
            old_instance = session.scalar(
                select(AssetInstance).where(
                    AssetInstance.asset_id == asset_id,
                    AssetInstance.person_id == source_person_id,
                    AssetInstance.deleted_at.is_(None),
                )
            )
            if old_instance and not old_instance.fixed_person:
                old_path = Path(old_instance.path)
                subfolder = "favourites" if old_instance.favourite else "photos"
                new_path = new_dir / subfolder / old_path.name
                try:
                    final = _safe_move(old_path, new_path)
                    old_instance.person_id = new_person.id
                    old_instance.path = str(final.resolve())
                    instances_created += 1
                except FileNotFoundError:
                    log.warning("Instance %s missing during split — creating copy", old_path)
                    result = materialize_assignment(session, asset_id, new_person.id, data_root)
                    if result:
                        instances_created += 1
            else:
                result = materialize_assignment(session, asset_id, new_person.id, data_root)
                if result:
                    instances_created += 1
        else:
            result = materialize_assignment(session, asset_id, new_person.id, data_root)
            if result:
                instances_created += 1

    session.flush()
    log.info(
        "Split %d faces from person %d → new person %d (%d instances)",
        faces_moved, source_person_id, new_person.id, instances_created,
    )
    return {
        "new_person_id": new_person.id,
        "faces_moved": faces_moved,
        "instances_created": instances_created,
    }
