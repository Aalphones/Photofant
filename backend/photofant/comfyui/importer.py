"""ComfyUI output selection, import, and defensive cleanup helpers."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image
from sqlalchemy.orm import Session

from photofant.comfyui.client import ComfyUIClient, ComfyUIError
from photofant.comfyui.introspect import SAVE_IMAGE_CLASSES
from photofant.config import get_data_root
from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
from photofant.db.models import AssetInstance, Person, Version
from photofant.media.person_folders import ensure_person_folder
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)

_PHOTOFANT_OUTPUT_TITLE = "Photofant Output"
_VERSION_TYPE = "comfyui"


@dataclass(frozen=True)
class ComfyUIOutputRef:
    filename: str
    subfolder: str = ""
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class ImportedComfyUIVersion:
    version_id: int
    version_type: str
    path: str
    is_current: bool
    params: dict[str, Any] | None
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
) -> ImportedComfyUIVersion:
    instance = (
        session.query(AssetInstance)
        .filter(AssetInstance.asset_id == asset_id, AssetInstance.deleted_at.is_(None))
        .first()
    )
    if instance is None:
        raise ValueError(f"Asset {asset_id} nicht gefunden oder geloescht")

    person = session.get(Person, instance.person_id)
    if person is None:
        raise ValueError(f"Person {instance.person_id} nicht gefunden")

    image_bytes, local_source_path = read_comfyui_output(client, output, output_dir)
    destination = _write_edit_file(person, output.filename, image_bytes)
    width, height = _read_image_size(destination, output)

    siblings = (
        session.query(Version)
        .filter(Version.instance_id == instance.id, Version.is_current.is_(True))
        .all()
    )
    for sibling in siblings:
        sibling.is_current = False

    version_params = {
        **params,
        "source_filename": output.filename,
        "source_subfolder": output.subfolder,
        "width": width,
        "height": height,
    }
    version = Version(
        instance_id=instance.id,
        face_id=None,
        type=_VERSION_TYPE,
        parent_id=None,
        path=str(destination.resolve()),
        is_current=True,
        params=version_params,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(version)
    session.commit()
    session.refresh(version)

    generate_version_thumbnails(version.id, destination)
    log.info("comfyui import: asset %d -> version %d (%s)", asset_id, version.id, output.filename)

    return ImportedComfyUIVersion(
        version_id=version.id,
        version_type=version.type or _VERSION_TYPE,
        path=version.path,
        is_current=version.is_current,
        params=version.params,
        thumbnail_url=f"/api/versions/{version.id}/thumbnail",
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


def generate_version_thumbnails(version_id: int, file_path: Path) -> None:
    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for thumb_size in (256, 512):
        try:
            thumb = generate_thumbnail(file_path, thumb_size)
            store_thumbnail(cache_path, version_id, thumb_size, thumb, "edit")
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


def _read_image_size(destination: Path, output: ComfyUIOutputRef) -> tuple[int | None, int | None]:
    if output.width is not None and output.height is not None:
        return output.width, output.height
    try:
        with Image.open(destination) as image:
            return image.size
    except Exception:
        return None, None


def _safe_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None
