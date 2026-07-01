"""ComfyUI output selection, import, and defensive cleanup helpers."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from photofant.comfyui.client import ComfyUIClient, ComfyUIError
from photofant.comfyui.introspect import SAVE_IMAGE_CLASSES
from photofant.config import get_data_root
from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
from photofant.db.models import Asset, AssetInstance, Person, ProcessingLedger, ReviewItem
from photofant.media.meta import read_meta
from photofant.media.person_folders import ensure_person_folder
from photofant.media.phash import compute_phash, find_similar
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)

_PHOTOFANT_OUTPUT_TITLE = "Photofant Output"


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class ComfyUIOutputRef:
    filename: str
    subfolder: str = ""
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class ImportedComfyUIAsset:
    """Result of importing a ComfyUI output as its own Asset (ADR-013).

    Replaces the former Version-based import — the edit is now a full pipeline
    asset linked back to its source via `original_id`.
    """

    asset_id: int
    source_asset_id: int
    path: str
    thumbnail_url: str
    local_source_path: Path | None


def select_default_output_node_id(template: dict[str, Any]) -> str:
    """Return the single SaveImage-compatible node that default auto-import may read."""
    marked_nodes: list[str] = []
    save_nodes: list[str] = []

    for node_id, node_data in template.items():
        if not isinstance(node_data, dict):
            continue
        if node_data.get("class_type") not in SAVE_IMAGE_CLASSES:
            continue
        save_nodes.append(str(node_id))
        meta = node_data.get("_meta", {})
        title = meta.get("title", "") if isinstance(meta, dict) else ""
        if title == _PHOTOFANT_OUTPUT_TITLE:
            marked_nodes.append(str(node_id))

    if len(marked_nodes) == 1:
        return marked_nodes[0]
    if len(marked_nodes) > 1:
        raise ValueError(
            f'Mehrere Save-Nodes mit Titel "{_PHOTOFANT_OUTPUT_TITLE}" gefunden. '
            "Genau ein kuratierter Output ist erlaubt."
        )
    if len(save_nodes) == 1:
        return save_nodes[0]
    if not save_nodes:
        raise ValueError(
            "Workflow hat keinen SaveImage-kompatiblen Output. "
            f'Bitte einen SaveImage-Node mit Titel "{_PHOTOFANT_OUTPUT_TITLE}" anlegen.'
        )
    raise ValueError(
        "Workflow hat mehrere unmarkierte Outputs. "
        f'Bitte genau den zu importierenden Save-Node "{_PHOTOFANT_OUTPUT_TITLE}" nennen.'
    )


def select_output_from_history(
    history: dict[str, Any],
    prompt_id: str,
    output_node_id: str,
) -> ComfyUIOutputRef:
    entry = history.get(prompt_id)
    if not isinstance(entry, dict):
        raise ValueError(f"ComfyUI-History enthaelt keinen Eintrag fuer Prompt {prompt_id}")

    outputs = entry.get("outputs", {})
    if not isinstance(outputs, dict):
        raise ValueError(f"ComfyUI-History fuer Prompt {prompt_id} enthaelt keine Outputs")

    node_output = outputs.get(output_node_id)
    if not isinstance(node_output, dict):
        raise ValueError(f"ComfyUI-History enthaelt keinen Output fuer Save-Node {output_node_id}")

    images = node_output.get("images", [])
    found_count = len(images) if isinstance(images, list) else 0
    if not isinstance(images, list) or found_count != 1:
        raise ValueError(f"Save-Node {output_node_id} muss genau ein Bild liefern; gefunden: {found_count}")

    image = images[0]
    if not isinstance(image, dict) or not image.get("filename"):
        raise ValueError(f"Save-Node {output_node_id} liefert kein importierbares Bild")

    return ComfyUIOutputRef(
        filename=str(image["filename"]),
        subfolder=str(image.get("subfolder", "")),
        width=_safe_int(image.get("width")),
        height=_safe_int(image.get("height")),
    )


def import_comfyui_output(
    session: Session,
    client: ComfyUIClient,
    *,
    asset_id: int,
    output: ComfyUIOutputRef,
    output_dir: str,
    params: dict[str, Any],
) -> ImportedComfyUIAsset:
    """Import a ComfyUI result as a full new Asset, linked via `original_id` (ADR-013).

    Runs the same pipeline steps as a normal photo import (hash, `ProcessingLedger`,
    pHash + dupe review) but stays synchronous — the caller (async context) must
    additionally await `enqueue_post_import_pipeline([(asset_id, path)])` since job
    enqueueing is async and this function is also invoked from worker threads.
    """
    source_instance = (
        session.query(AssetInstance)
        .filter(AssetInstance.asset_id == asset_id, AssetInstance.deleted_at.is_(None))
        .first()
    )
    if source_instance is None:
        raise ValueError(f"Asset {asset_id} nicht gefunden oder geloescht")

    person = session.get(Person, source_instance.person_id)
    if person is None:
        raise ValueError(f"Person {source_instance.person_id} nicht gefunden")

    image_bytes, local_source_path = read_comfyui_output(client, output, output_dir)
    destination = _write_edit_file(person, output.filename, image_bytes)
    meta = read_meta(destination)

    existing_asset = session.query(Asset).filter(Asset.content_hash == meta.content_hash).first()
    if existing_asset is not None:
        destination.unlink(missing_ok=True)
        raise ValueError(
            f"ComfyUI-Ergebnis ist identisch mit vorhandenem Asset {existing_asset.id} — kein Import noetig"
        )

    new_asset = Asset(
        content_hash=meta.content_hash,
        source=meta.source,
        width=meta.width,
        height=meta.height,
        file_size=meta.file_size,
        format=meta.format,
        generation_meta={**(meta.generation_meta or {}), **params, "source_filename": output.filename,
                          "source_subfolder": output.subfolder},
        original_id=asset_id,
        created_at=_now_utc(),
        imported_at=_now_utc(),
    )
    session.add(new_asset)
    session.flush()

    new_instance = AssetInstance(
        asset_id=new_asset.id,
        person_id=person.id,
        path=str(destination.resolve()),
    )
    session.add(new_instance)
    session.add(ProcessingLedger(content_hash=meta.content_hash))

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        destination.unlink(missing_ok=True)
        raise ValueError("ComfyUI-Ergebnis wurde bereits parallel importiert") from None

    try:
        phash_val = compute_phash(destination)
        new_asset.phash = phash_val
        session.commit()

        from photofant.settings import load_settings

        dupe_threshold = load_settings()["dupe_threshold"]
        similar = find_similar(session, phash_val, new_asset.id, dupe_threshold)
        for other_id, distance in similar:
            asset_a_id, asset_b_id = min(new_asset.id, other_id), max(new_asset.id, other_id)
            stmt = sqlite_insert(ReviewItem).values(
                type="dupe_candidate",
                asset_a_id=asset_a_id,
                asset_b_id=asset_b_id,
                phash_distance=distance,
                created_at=_now_utc(),
            ).on_conflict_do_nothing()
            session.execute(stmt)
        if similar:
            session.commit()
    except Exception:
        log.exception("pHash/dupe-detection failed for ComfyUI import %s", destination)
        session.rollback()

    generate_asset_thumbnails(new_asset.id, destination)
    log.info(
        "comfyui import (ADR-013): source asset %d -> new asset %d, original_id set (%s)",
        asset_id, new_asset.id, output.filename,
    )

    return ImportedComfyUIAsset(
        asset_id=new_asset.id,
        source_asset_id=asset_id,
        path=str(destination.resolve()),
        thumbnail_url=f"/api/assets/{new_asset.id}/thumbnail",
        local_source_path=local_source_path,
    )


def read_comfyui_output(
    client: ComfyUIClient,
    output: ComfyUIOutputRef,
    output_dir: str,
) -> tuple[bytes, Path | None]:
    try:
        return client.view_image(output.filename, output.subfolder), None
    except ComfyUIError:
        pass

    local_path = resolve_local_output_path(output_dir, output.filename, output.subfolder)
    if local_path is not None and local_path.is_file():
        return local_path.read_bytes(), local_path

    raise FileNotFoundError(
        f"Datei '{output.filename}' nicht abrufbar - weder via ComfyUI noch in output_dir"
    )


def resolve_local_output_path(output_dir: str, filename: str, subfolder: str = "") -> Path | None:
    if not output_dir:
        return None

    base = Path(output_dir).resolve()
    candidate = base / subfolder / filename if subfolder else base / filename
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        return None
    return resolved


def delete_imported_local_output(output_dir: str, output: ComfyUIOutputRef) -> bool:
    local_path = resolve_local_output_path(output_dir, output.filename, output.subfolder)
    if local_path is None or not local_path.is_file():
        return False
    try:
        local_path.unlink()
        log.info("Deleted auto-imported ComfyUI output %s", local_path)
        return True
    except OSError:
        log.warning("Could not delete auto-imported ComfyUI output %s", local_path)
        return False


def generate_asset_thumbnails(asset_id: int, file_path: Path) -> None:
    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for thumb_size in (256, 512):
        try:
            thumb = generate_thumbnail(file_path, thumb_size)
            store_thumbnail(cache_path, asset_id, thumb_size, thumb)
        except Exception:
            log.warning("Thumbnail-Generierung fehlgeschlagen fuer %s (size %d)", file_path, thumb_size)


def _write_edit_file(person: Person, filename: str, image_bytes: bytes) -> Path:
    data_root_path = Path(get_data_root())
    person_dir = ensure_person_folder(data_root_path, person)
    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(filename).suffix.lower() or ".png"
    destination = edits_dir / f"comfyui_{uuid.uuid4().hex[:12]}{extension}"
    destination.write_bytes(image_bytes)
    return destination


def _safe_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None
