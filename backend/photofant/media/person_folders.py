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

from photofant.db.models import Asset, AssetInstance, Face, Person, SmartTrigger

log = logging.getLogger(__name__)

_PERSON_SUBFOLDERS = ["photos", "favourites", "faces", "edits"]


def _sanitize_folder_name(name: str) -> str:
    """Strip filesystem-invalid characters from a name for use as a folder name."""
    invalid = set(r'\/:*?"<>|')
    sanitized = "".join(c for c in name if c not in invalid and ord(c) >= 32)
    return sanitized.strip(". ")


def person_folder_name(person: Person) -> str:
    if person.is_unknown:
        return "_unknown"
    if person.name:
        sanitized = _sanitize_folder_name(person.name)
        if sanitized:
            return sanitized
    return f"person_{person.id}"


def ensure_person_folder(data_root: Path, person: Person) -> Path:
    folder = data_root / person_folder_name(person)
    for sub in _PERSON_SUBFOLDERS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    return folder


def person_id_from_path(
    file_path: Path,
    data_root: Path,
    session: Session | None = None,
) -> int | None:
    """Extract the person DB id from a file path inside a person folder.

    Handles both legacy person_{id}/ folders and current named folders.
    Pass a session to resolve named folders via the DB.
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

    # Legacy format: person_{id}/
    if folder.startswith("person_"):
        try:
            return int(folder[7:])
        except ValueError:
            pass

    # Named folder: look up by sanitized person name
    if session is not None:
        persons = session.scalars(
            select(Person).where(Person.is_unknown.is_(False), Person.name.isnot(None))
        ).all()
        for person in persons:
            if person_folder_name(person) == folder:
                return person.id

    return None


def is_importable_person_subfolder(
    file_path: Path,
    data_root: Path,
    session: Session | None = None,
) -> bool:
    """True if the file sits in a person folder's photos/ or favourites/ dir."""
    try:
        relative = file_path.resolve().relative_to(data_root.resolve())
    except ValueError:
        return False

    parts = relative.parts
    if len(parts) < 3:
        return False

    folder = parts[0]
    subfolder = parts[1]

    if subfolder not in ("photos", "favourites"):
        return False

    # Legacy format: person_{id}/
    if folder.startswith("person_"):
        return True

    # Named folder: verify via DB
    if session is not None:
        return person_id_from_path(file_path, data_root, session) is not None

    return False


def rename_person_folder(
    session: Session,
    person: Person,
    old_folder_name: str,
    data_root: Path,
) -> int:
    """Rename a person's folder on disk and update all path references in the DB.

    Returns the number of updated path entries (instances + face crops).
    """
    new_folder_name = person_folder_name(person)
    if old_folder_name == new_folder_name:
        return 0

    old_dir = data_root / old_folder_name
    new_dir = data_root / new_folder_name

    if not old_dir.exists():
        # Fallback: legacy person_{id} folder (created before named-folder convention)
        legacy_dir = data_root / f"person_{person.id}"
        if legacy_dir.exists() and legacy_dir != new_dir:
            old_dir = legacy_dir
        else:
            ensure_person_folder(data_root, person)
            return 0

    if new_dir.exists():
        log.warning(
            "Cannot rename person folder %s → %s: target already exists",
            old_folder_name, new_folder_name,
        )
        return 0

    old_dir.rename(new_dir)
    log.info("Renamed person folder %s → %s", old_folder_name, new_folder_name)

    old_prefix = str(old_dir.resolve())
    new_prefix = str(new_dir.resolve())
    updated = 0

    instances = session.scalars(
        select(AssetInstance).where(
            AssetInstance.person_id == person.id,
            AssetInstance.deleted_at.is_(None),
        )
    ).all()
    for instance in instances:
        if instance.path.startswith(old_prefix):
            instance.path = new_prefix + instance.path[len(old_prefix):]
            updated += 1

    faces = session.scalars(
        select(Face).where(Face.person_id == person.id)
    ).all()
    for face in faces:
        if face.crop_path.startswith(old_prefix):
            face.crop_path = new_prefix + face.crop_path[len(old_prefix):]
            updated += 1

    session.flush()
    return updated


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

    # ADR-013: assets linked via original_id are edits, not photos — keep them
    # physically distinguishable even when clustering moves them to a new person.
    asset = session.get(Asset, asset_id)
    is_edit_child = asset is not None and asset.original_id is not None

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

    # Don't move the _unknown instance if there are still faces assigned to _unknown
    # for this asset (e.g. noise-cluster faces). Moving it would leave _unknown with a
    # portrait_face_id but count=0, making the Unknown tab appear broken.
    remaining_unknown_faces: int = 0
    if unknown_person and unknown_instance is not None:
        remaining_unknown_faces = session.scalar(
            select(func.count())
            .select_from(Face)
            .where(Face.asset_id == asset_id, Face.person_id == unknown_person.id)
        ) or 0

    can_move_unknown = (
        unknown_instance is not None
        and not unknown_instance.fixed_person
        and real_instance_count == 0
        and remaining_unknown_faces == 0
    )

    if can_move_unknown:
        source_path = Path(unknown_instance.path)
        if unknown_instance.favourite:
            subfolder = "favourites"
        elif is_edit_child:
            subfolder = "edits"
        else:
            subfolder = "photos"
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
        dest = person_dir / ("edits" if is_edit_child else "photos") / source_path.name

        try:
            final = _safe_copy(source_path, dest)
        except OSError:
            log.error("Cannot copy for asset %d — file error: %s", asset_id, source_path)
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


def move_face_crop_to_assigned_folder(
    session: Session,
    face_id: int,
    data_root: Path,
) -> bool:
    """Move a single face's crop into its assigned person's faces/ dir.

    Repairs a crop that lags behind its DB assignment — e.g. a fixed-person upload
    whose best face was assigned to the person but left behind in _unknown/faces.
    No-op (returns False) when the face has no person, belongs to _unknown, is
    already in place, or its file is missing.
    """
    face = session.get(Face, face_id)
    if face is None or face.person_id is None:
        return False

    person = session.get(Person, face.person_id)
    if person is None or person.is_unknown:
        return False

    faces_dir = ensure_person_folder(data_root, person) / "faces"
    old_path = Path(face.crop_path)
    new_path = faces_dir / old_path.name
    if old_path.resolve() == new_path.resolve():
        return False

    try:
        final = _safe_move(old_path, new_path)
    except FileNotFoundError:
        log.warning(
            "Face crop %s missing — cannot move face %d to its person folder",
            old_path, face_id,
        )
        return False

    face.crop_path = str(final.resolve())
    session.flush()
    return True


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


# ── orphaned-instance pruning ────────────────────────────────────────────


def _delete_instance(session: Session, instance: AssetInstance) -> None:
    """Drop an instance row and its file (a per-person copy that's safe to lose)."""
    old_path = Path(instance.path)
    if old_path.exists():
        try:
            old_path.unlink()
            log.info("Pruned orphaned instance file %s", old_path)
        except OSError:
            log.warning("Could not delete orphaned instance file %s", old_path)
    session.delete(instance)


def _move_instance_to_unknown(
    session: Session,
    instance: AssetInstance,
    unknown_person: Person,
    data_root: Path,
) -> None:
    """Reassign an orphaned last instance to _unknown instead of deleting it."""
    unknown_dir = ensure_person_folder(data_root, unknown_person)
    subfolder = "favourites" if instance.favourite else "photos"
    source = Path(instance.path)
    dest = unknown_dir / subfolder / source.name
    try:
        final = _safe_move(source, dest)
        instance.path = str(final.resolve())
    except FileNotFoundError:
        log.warning("Cannot move orphaned instance %s to _unknown — file missing", source)
    instance.person_id = unknown_person.id
    instance.fixed_person = False
    log.info("Moved orphaned instance for asset %d to _unknown", instance.asset_id)


def prune_orphaned_instances(
    session: Session,
    asset_id: int | None,
    data_root: Path,
) -> dict[str, int]:
    """Reconcile an asset's instances with its faces after a face mutation.

    Runs after delete / reassign so the gallery's person filter and the on-disk
    person folders follow the faces. An instance is *orphaned* when its person
    has no remaining face on this asset. Orphans are handled so a photo is never
    destroyed just because its last face was removed:

      - The photo still lives under a face-backed person → drop the orphan's row
        and its (copied) file.
      - It is the asset's last instance → move it to `_unknown` instead of
        deleting it. A face-less photo lands in the catch-all, not the trash.

    Because this only runs after a face operation, a photo that never had a face
    (e.g. a landscape deliberately dropped onto a person) is never touched here.

    Returns {"removed": n, "moved_to_unknown": m}.
    """
    if asset_id is None:
        return {"removed": 0, "moved_to_unknown": 0}

    unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
    if unknown_person is None:
        return {"removed": 0, "moved_to_unknown": 0}

    instances = session.scalars(
        select(AssetInstance).where(
            AssetInstance.asset_id == asset_id,
            AssetInstance.deleted_at.is_(None),
        )
    ).all()

    def has_face(person_id: int) -> bool:
        count: int = session.scalar(
            select(func.count())
            .select_from(Face)
            .where(Face.asset_id == asset_id, Face.person_id == person_id)
        ) or 0
        return count > 0

    orphans = [inst for inst in instances if not has_face(inst.person_id)]
    if not orphans:
        return {"removed": 0, "moved_to_unknown": 0}

    face_backed = [inst for inst in instances if inst not in orphans]

    removed = 0
    moved = 0

    if face_backed:
        # The photo survives under a real face elsewhere → drop every orphan.
        for instance in orphans:
            _delete_instance(session, instance)
            removed += 1
    else:
        # No face-backed instance left. Keep exactly one, in _unknown, so the
        # photo isn't lost. Prefer an instance that's already in _unknown.
        survivor = next(
            (inst for inst in orphans if inst.person_id == unknown_person.id),
            orphans[0],
        )
        for instance in orphans:
            if instance is survivor:
                if instance.person_id != unknown_person.id:
                    _move_instance_to_unknown(session, instance, unknown_person, data_root)
                    moved += 1
            else:
                _delete_instance(session, instance)
                removed += 1

    session.flush()
    return {"removed": removed, "moved_to_unknown": moved}


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
    except OSError:
        log.warning("Face crop move failed during reassign for face %d — path not updated", face_id)

    materialize_assignment(session, asset_id, new_person_id, data_root, fixed=True)

    # Prune every instance this asset no longer has a face for — not just the
    # old person. The wrongly-assigned instance may belong to a third person
    # (e.g. an import-into-person assignment whose face never matched it).
    prune_orphaned_instances(session, asset_id, data_root)

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


def _resolve_person_smart_triggers(
    session: Session,
    person_id: int,
    successor_id: int | None,
) -> int:
    """Keep SmartTrigger.person_id from silently going stale.

    SQLite doesn't enforce the FK on SmartTrigger.person_id, so a trigger
    pointing at a person that was merged away or deleted would otherwise just
    stop matching forever — no error, just a dead trigger.

    successor_id=None → the person is gone with no replacement (delete):
      remove the trigger, there's nothing left to point at.
    successor_id set  → the identity lives on under another person (merge):
      repoint the trigger instead of losing it.

    Returns the number of triggers touched.
    """
    triggers = session.scalars(
        select(SmartTrigger).where(
            SmartTrigger.type == "person",
            SmartTrigger.person_id == person_id,
        )
    ).all()
    for trigger in triggers:
        if successor_id is None:
            session.delete(trigger)
        else:
            trigger.person_id = successor_id
    if triggers:
        log.info(
            "Smart-album trigger(s) referencing person %d %s (%d)",
            person_id,
            "removed" if successor_id is None else f"repointed to person {successor_id}",
            len(triggers),
        )
    session.flush()
    return len(triggers)


# ── delete a person ───────────────────────────────────────────────────


def delete_person(
    session: Session,
    person_id: int,
    data_root: Path,
) -> dict[str, object]:
    """Delete a person completely — faces and photos move to _unknown, folder + row are gone.

    Unlike merge_persons (name carry-over, fixed_person untouched), a deleted
    person's assignments are dissolved: nothing survives except the raw files,
    which land back in the catch-all, free to be re-matched by clustering.
    Any smart-album trigger pointing at this person is removed too — otherwise
    it would silently stop matching forever (SQLite enforces no FK here).

    Returns {faces_moved, instances_moved, asset_ids} — asset_ids is every asset
    touched, for the caller to trigger a smart-album re-evaluation.
    """
    person = session.get(Person, person_id)
    if person is None:
        raise ValueError(f"Person {person_id} not found")
    if person.is_unknown:
        raise ValueError("Cannot delete the unknown person")

    unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
    if unknown_person is None:
        raise ValueError("No _unknown person found — database inconsistent")

    unknown_dir = ensure_person_folder(data_root, unknown_person)
    affected_asset_ids: set[int] = set()

    faces = session.scalars(select(Face).where(Face.person_id == person_id)).all()
    faces_moved = 0
    for face in faces:
        face.person_id = unknown_person.id
        if face.asset_id is not None:
            affected_asset_ids.add(face.asset_id)
        old_crop = Path(face.crop_path)
        new_crop = unknown_dir / "faces" / old_crop.name
        try:
            final = _safe_move(old_crop, new_crop)
            face.crop_path = str(final.resolve())
        except FileNotFoundError:
            log.warning("Face crop %s missing while deleting person %d — skipping", old_crop, person_id)
        faces_moved += 1
    session.flush()

    instances = session.scalars(
        select(AssetInstance).where(
            AssetInstance.person_id == person_id,
            AssetInstance.deleted_at.is_(None),
        )
    ).all()

    instances_moved = 0
    for instance in instances:
        affected_asset_ids.add(instance.asset_id)
        existing_target = session.scalar(
            select(AssetInstance).where(
                AssetInstance.asset_id == instance.asset_id,
                AssetInstance.person_id == unknown_person.id,
                AssetInstance.deleted_at.is_(None),
            )
        )
        if existing_target is not None:
            # _unknown already has this asset — drop the duplicate instance/file.
            old_path = Path(instance.path)
            if old_path.exists():
                old_path.unlink()
            session.delete(instance)
            instances_moved += 1
            continue

        subfolder = "favourites" if instance.favourite else "photos"
        old_path = Path(instance.path)
        new_path = unknown_dir / subfolder / old_path.name
        try:
            final = _safe_move(old_path, new_path)
            instance.person_id = unknown_person.id
            instance.path = str(final.resolve())
            instance.fixed_person = False  # release for future clustering/matching
            instances_moved += 1
        except FileNotFoundError:
            log.warning("Instance file %s missing while deleting person %d — skipping", old_path, person_id)

    session.flush()

    # No successor — the identity is gone, any person-trigger pointing here dies with it.
    _resolve_person_smart_triggers(session, person_id, None)

    person_dir = data_root / person_folder_name(person)
    session.delete(person)
    session.flush()

    if person_dir.exists():
        shutil.rmtree(str(person_dir), ignore_errors=True)
        log.info("Removed person folder %s", person_dir)

    log.info(
        "Deleted person %d: %d faces + %d instances moved to _unknown",
        person_id, faces_moved, instances_moved,
    )
    return {
        "faces_moved": faces_moved,
        "instances_moved": instances_moved,
        "asset_ids": list(affected_asset_ids),
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

    # Carry name over when merging a named person into a nameless cluster
    if from_person.name is not None and into_person.name is None:
        into_person.name = from_person.name
        session.flush()
        log.info("Carried name %r from person %d to person %d", into_person.name, from_person_id, into_person_id)

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
        _resolve_person_smart_triggers(session, from_person_id, into_person_id)

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

    if faces_moved == 0:
        # No faces matched — the new person would be an empty nameless fragment; clean it up.
        session.delete(new_person)
        session.flush()
        log.warning("split_faces: no faces moved from person %d — cleaned up empty person", source_person_id)
        return {"new_person_id": None, "faces_moved": 0, "instances_created": 0}

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
