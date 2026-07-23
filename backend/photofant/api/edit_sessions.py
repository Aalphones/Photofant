"""Edit-Session API — CPU-only image editor (P8)

POST /edit-sessions                      → create session, returns session_key
GET  /edit-sessions/{key}                → session state + step list
POST /edit-sessions/{key}/steps          → apply op, store step preview
POST /edit-sessions/{key}/rollback       → truncate steps after to_seq
GET  /edit-sessions/{key}/preview/{seq}  → JPEG (seq=0 → original preview)
POST /edit-sessions/{key}/save           → final render + version row (Phase 4)

GET  /versions/{id}/thumbnail            → JPEG thumbnail for saved version
GET  /versions/{id}/file                 → original version file
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.config import get_data_root
from photofant.db.cache import (
    append_edit_step,
    create_edit_session,
    get_cache_db_path,
    get_edit_session,
    get_edit_step_preview,
    get_edit_steps,
    get_thumbnail,
    init_cache_db,
    store_thumbnail,
    truncate_steps_after,
)
from photofant.db.models import Asset, AssetInstance, Face, Person, Version
from photofant.db.session import SessionLocal as _SessionLocal
from photofant.db.session import get_session
from photofant.media.ops import ModelNotAvailableError, apply_op, is_orientation_only
from photofant.media.orientation_overwrite import overwrite_face, overwrite_instance, overwrite_version
from photofant.media.person_folders import ensure_person_folder
from photofant.media.thumbnails import generate_thumbnail
from photofant.media.versions import (
    generate_version_thumbnail as _generate_version_thumbnail,
)
from photofant.media.versions import (
    unset_current_versions as _unset_current_versions,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/edit-sessions")
versions_router = APIRouter(prefix="/versions")

DbSession = Annotated[Session, Depends(get_session)]

_PREVIEW_MAX_PX = 1024
_PREVIEW_JPEG_QUALITY = 88


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class EditTarget(BaseModel):
    kind: str  # instance | face | version
    id: int


class CreateSessionRequest(BaseModel):
    target: EditTarget


class CreateSessionResponse(BaseModel):
    session_key: str
    original_preview_url: str


class StepInfo(BaseModel):
    seq: int
    op: str
    params: dict[str, Any]  # type: ignore[type-arg]


class SessionStateResponse(BaseModel):
    session_key: str
    kind: str
    target_id: int
    steps: list[StepInfo]


class ApplyStepRequest(BaseModel):
    op: str
    params: dict[str, Any]  # type: ignore[type-arg]


class StepResponse(BaseModel):
    seq: int
    preview_url: str


class RollbackRequest(BaseModel):
    to_seq: int


class RollbackResponse(BaseModel):
    seq: int


class SaveRequest(BaseModel):
    mode: Literal["overwrite", "new_copy"]


class ResDto(BaseModel):
    width: int
    height: int


class VersionDto(BaseModel):
    id: int
    type: str | None
    parent_id: int | None
    path: str
    is_current: bool
    params: dict | None  # type: ignore[type-arg]
    created_at: datetime | None
    res: ResDto | None
    thumbnail_url: str


class VersionGalleryDto(BaseModel):
    id: int
    type: str | None
    is_current: bool
    params: dict | None  # type: ignore[type-arg]
    created_at: datetime | None
    thumbnail_url: str
    parent_asset_id: int | None
    width: int | None
    height: int | None


class OrientationOverwriteDto(BaseModel):
    """Response for an orientation-only save on a face/instance target — no Version row exists."""

    kind: Literal["face", "instance"]
    target_id: int
    width: int
    height: int
    thumbnail_url: str


class VersionsPage(BaseModel):
    items: list[VersionGalleryDto]
    total: int
    page: int
    page_size: int


# ── Render pipeline ───────────────────────────────────────────────────────────

def _render_image(
    source_path: Path,
    steps: list[dict[str, Any]],  # type: ignore[type-arg]
    max_px: int | None = _PREVIEW_MAX_PX,
) -> Image.Image:
    """Apply all steps to the original image and return a PIL Image.

    max_px=None → full original resolution (final render for save).
    max_px=1024 → preview resolution.
    """
    try:
        with Image.open(source_path) as raw:
            img: Image.Image = ImageOps.exif_transpose(raw) or raw
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGB")
            if img.mode == "L":
                img = img.convert("RGB")
            if max_px is not None:
                img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
            for step in steps:
                img = apply_op(img, step["op"], step["params_dict"])
            img.load()
            return img
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"Cannot render image: {exc}") from exc


def _image_to_jpeg(img: Image.Image) -> bytes:
    if img.mode in ("RGBA", "LA", "PA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1]
        background.paste(img, mask=alpha)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_PREVIEW_JPEG_QUALITY)
    return buf.getvalue()


def _render_steps(
    source_path: Path,
    steps: list[dict[str, Any]],  # type: ignore[type-arg]
    preview_max: int = _PREVIEW_MAX_PX,
) -> bytes:
    img = _render_image(source_path, steps, max_px=preview_max)
    return _image_to_jpeg(img)


# ── Final-render save helpers ────────────────────────────────────────────────

def _determine_output_format(
    steps: list[dict[str, Any]],  # type: ignore[type-arg]
    img: Image.Image,
) -> tuple[str, str, int]:
    """Returns (pil_format, file_extension, quality)."""
    for step in reversed(steps):
        if step["op"] == "convert":
            params = step["params_dict"]
            fmt = params.get("format", "png")
            quality = params.get("quality", 92)
            if fmt == "jpeg":
                return ("JPEG", "jpg", quality)
            return ("PNG", "png", 0)
    if img.mode in ("RGBA", "LA", "PA"):
        return ("PNG", "png", 0)
    return ("JPEG", "jpg", 92)


def _save_image_to_disk(
    img: Image.Image, path: Path, pil_format: str, quality: int
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pil_format == "JPEG":
        if img.mode in ("RGBA", "LA", "PA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(path, format="JPEG", quality=quality)
    else:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        img.save(path, format="PNG")


def _build_version_dto(version: Version, width: int, height: int) -> VersionDto:
    return VersionDto(
        id=version.id,
        type=version.type,
        parent_id=version.parent_id,
        path=version.path,
        is_current=version.is_current,
        params=version.params,
        created_at=version.created_at,
        res=ResDto(width=width, height=height),
        thumbnail_url=f"/api/versions/{version.id}/thumbnail",
    )


def _determine_version_type(steps: list[dict[str, Any]]) -> str:  # type: ignore[type-arg]
    if not steps:
        return "edit"
    if len(steps) == 1:
        return steps[0]["op"]
    return steps[0]["op"]


def _build_version_params(steps: list[dict[str, Any]], width: int, height: int) -> dict[str, Any]:  # type: ignore[type-arg]
    return {
        "steps": [{"op": step["op"], "params": step["params_dict"]} for step in steps],
        "width": width,
        "height": height,
    }


# ── Path resolution ───────────────────────────────────────────────────────────

def _resolve_source_path(target: EditTarget, db: Session) -> Path:
    """Map target (kind, id) to a readable file path."""
    if target.kind == "instance":
        row = (
            db.query(AssetInstance.path)
            .join(Asset, AssetInstance.asset_id == Asset.id)
            .filter(Asset.id == target.id)
            .filter(AssetInstance.deleted_at.is_(None))
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Asset instance not found")
        return Path(row.path)

    if target.kind == "face":
        face = db.query(Face).filter(Face.id == target.id).first()
        if face is None:
            raise HTTPException(status_code=404, detail="Face not found")
        return Path(face.crop_path)

    if target.kind == "version":
        version = db.query(Version).filter(Version.id == target.id).first()
        if version is None:
            raise HTTPException(status_code=404, detail="Version not found")
        return Path(version.path)

    raise HTTPException(status_code=422, detail=f"Unsupported target kind: {target.kind!r}")


def _resolve_save_context(
    session_row: dict[str, Any],  # type: ignore[type-arg]
    db: Session,
) -> tuple[int | None, int | None, int | None, int]:
    """Resolve instance_id, face_id, parent_version_id, person_id from session."""
    kind = session_row["kind"]
    target_id = session_row["target_id"]

    if kind == "instance":
        instance = (
            db.query(AssetInstance)
            .join(Asset, AssetInstance.asset_id == Asset.id)
            .filter(Asset.id == target_id, AssetInstance.deleted_at.is_(None))
            .first()
        )
        if instance is None:
            raise HTTPException(status_code=404, detail="Asset instance not found")
        return instance.id, None, None, instance.person_id

    if kind == "face":
        face = db.get(Face, target_id)
        if face is None:
            raise HTTPException(status_code=404, detail="Face not found")
        return None, face.id, None, face.person_id or 1

    if kind == "version":
        parent_version = db.get(Version, target_id)
        if parent_version is None:
            raise HTTPException(status_code=404, detail="Version not found")
        if parent_version.instance_id is not None:
            instance = db.get(AssetInstance, parent_version.instance_id)
            person_id = instance.person_id if instance else 1
        else:
            face = db.get(Face, parent_version.face_id)
            person_id = face.person_id if face else 1
        return parent_version.instance_id, parent_version.face_id, parent_version.id, person_id

    raise HTTPException(status_code=422, detail=f"Unsupported session kind: {kind!r}")


# ── Face-Dedupe nach Version-Save (§8.3) ─────────────────────────────────────

_FACE_PADDING_VERSION = 40  # px, same as face_job default
_FACE_CROP_QUALITY = 92


def _run_version_face_dedupe(version_id: int, instance_id: int | None, face_id_src: int | None) -> None:
    """Detect faces in a newly saved version, skip quasi-duplicates via face embeddings (§8.3).

    Runs in a thread after save so the HTTP response is already sent.
    No-op when buffalo_l is unavailable; logged at INFO level.

    P9-Upscale note: is_upscale_source flag is always False here — upscale ops
    (§8.3 step 5: keep even if quasi-identical when resolution is clearly higher)
    are gated in P9. The infrastructure is wired up; only the caller sets the flag.
    """
    import numpy as np

    from photofant.config import get_data_root
    from photofant.inference.adapters.buffalo_l import resolve_buffalo_l
    from photofant.settings import load_settings

    engine = resolve_buffalo_l()
    if engine is None:
        log.info("Face-Dedupe skipped for version %d — buffalo_l not available", version_id)
        return

    similarity_threshold = load_settings()["face_dedupe_similarity_threshold"]

    with _SessionLocal() as session:
        version = session.get(Version, version_id)
        if version is None:
            return
        version_path = Path(version.path)
        if not version_path.exists():
            log.warning("Face-Dedupe: version %d file not found at %s", version_id, version.path)
            return

        # Collect existing embeddings for lineage comparison (L2-normalized, ADR-001)
        existing_embeddings: list[np.ndarray] = []
        if instance_id is not None:
            asset_id_row = (
                session.query(AssetInstance)
                .filter(AssetInstance.id == instance_id)
                .first()
            )
            if asset_id_row is not None:
                existing_embeddings = [
                    np.frombuffer(bytes(face.embedding), dtype=np.float32)
                    for face in session.query(Face).filter(
                        Face.asset_id == asset_id_row.asset_id,
                        Face.embedding.isnot(None),
                    ).all()
                ]
        elif face_id_src is not None:
            source_face = session.get(Face, face_id_src)
            if source_face is not None and source_face.embedding:
                existing_embeddings = [np.frombuffer(bytes(source_face.embedding), dtype=np.float32)]

        unknown_person = session.query(Person).filter_by(is_unknown=True).first()
        if unknown_person is None:
            log.error("Face-Dedupe: _unknown person row missing")
            return
        unknown_person_id = unknown_person.id

    from PIL import Image as PILImage

    try:
        image_pil = PILImage.open(version_path).convert("RGB")
        image_np = np.array(image_pil, dtype=np.uint8)
    except Exception:
        log.exception("Face-Dedupe: failed to open version image %s", version_path)
        return

    try:
        faces_detected = engine.detect(image_np)
    except Exception:
        log.exception("Face-Dedupe: buffalo_l detection failed for version %d", version_id)
        return

    if not faces_detected:
        log.info("Face-Dedupe: no faces in version %d", version_id)
        return

    data_root = Path(get_data_root())
    faces_dir = data_root / "_unknown" / "faces"
    faces_dir.mkdir(parents=True, exist_ok=True)

    for face_index, face_dict in enumerate(faces_detected):
        bbox = face_dict["bbox"]
        score = face_dict.get("score")
        age = face_dict.get("age")
        embedding = face_dict.get("embedding")

        height_img, width_img = image_np.shape[:2]
        x1, y1, x2, y2 = (int(round(v)) for v in bbox)
        x1 = max(0, x1 - _FACE_PADDING_VERSION)
        y1 = max(0, y1 - _FACE_PADDING_VERSION)
        x2 = min(width_img, x2 + _FACE_PADDING_VERSION)
        y2 = min(height_img, y2 + _FACE_PADDING_VERSION)
        crop_np = image_np[y1:y2, x1:x2]

        crop_filename = f"v{version_id}_{face_index}.jpg"
        crop_path = faces_dir / crop_filename
        try:
            from PIL import Image as _PILImage
            _PILImage.fromarray(crop_np).save(str(crop_path), "JPEG", quality=_FACE_CROP_QUALITY)
        except Exception:
            log.exception("Face-Dedupe: failed to save face crop for version %d idx %d", version_id, face_index)
            continue

        # P9-Upscale flag (always False in P8 — upscale ops are P9-gated)
        is_upscale_source = False

        # Check quasi-identity against lineage faces (cosine via dot product, L2-normalized)
        if embedding is not None and not is_upscale_source:
            is_duplicate = any(
                float(np.dot(embedding, existing)) >= similarity_threshold
                for existing in existing_embeddings
            )
            if is_duplicate:
                log.info(
                    "Face-Dedupe: face %d of version %d is quasi-identical — skipped",
                    face_index, version_id,
                )
                crop_path.unlink(missing_ok=True)
                continue

        # New distinct face — create Face row
        resolution = crop_np.shape[0] * crop_np.shape[1]
        embedding_bytes = embedding.astype("float32").tobytes() if embedding is not None else None

        with _SessionLocal() as session:
            face_row = Face(
                asset_id=None,
                person_id=unknown_person_id,
                source_version_id=version_id,
                crop_path=str(crop_path.resolve()),
                bbox={"x1": bbox[0], "y1": bbox[1], "x2": bbox[2], "y2": bbox[3]},
                padding=_FACE_PADDING_VERSION,
                embedding=embedding_bytes,
                score=score,
                age=age,
                origin="derived",
                origin_type="edit",
                is_upscaled=False,
                resolution=resolution,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(face_row)
            session.commit()
            saved_face_id = face_row.id

        log.info(
            "Face-Dedupe: new face %d for version %d (score=%.3f)",
            saved_face_id, version_id, score or 0.0,
        )

        # Thumbnail
        try:
            from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
            from photofant.media.thumbnails import generate_thumbnail
            cache_path = get_cache_db_path()
            init_cache_db(cache_path)
            thumb = generate_thumbnail(crop_path, size=256)
            store_thumbnail(cache_path, saved_face_id, size=256, data=thumb, target_kind="face")
        except Exception:
            log.exception("Face-Dedupe: thumbnail failed for face %d", saved_face_id)


# ── Orientation-only save (rotate/mirror overwrite the source, Phase 3) ──────

async def _save_orientation_overwrite(
    session_row: dict[str, Any],  # type: ignore[type-arg]
    steps: list[dict[str, Any]],  # type: ignore[type-arg]
    db: Session,
) -> VersionDto | OrientationOverwriteDto:
    kind = session_row["kind"]
    target_id = session_row["target_id"]
    loop = asyncio.get_event_loop()

    if kind == "version":
        version = db.get(Version, target_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Version not found")
        result = await loop.run_in_executor(None, overwrite_version, db, version, steps)
        return _build_version_dto(version, result["width"], result["height"])

    if kind == "face":
        face = db.get(Face, target_id)
        if face is None:
            raise HTTPException(status_code=404, detail="Face not found")
        result = await loop.run_in_executor(None, overwrite_face, db, face, steps)
        return OrientationOverwriteDto(
            kind="face",
            target_id=face.id,
            width=result["width"],
            height=result["height"],
            thumbnail_url=f"/api/faces/{face.id}/thumbnail",
        )

    if kind == "instance":
        # target_id is the asset id (create_session resolves instance targets by
        # asset), so re-run the same instance resolution save_session already
        # relies on elsewhere instead of guessing which physical copy to edit.
        instance_id, _face_id, _parent_version_id, _person_id = _resolve_save_context(session_row, db)
        instance = db.get(AssetInstance, instance_id) if instance_id is not None else None
        if instance is None:
            raise HTTPException(status_code=404, detail="Asset instance not found")
        result = await loop.run_in_executor(None, overwrite_instance, db, instance, steps)
        return OrientationOverwriteDto(
            kind="instance",
            target_id=result["asset_id"],
            width=result["width"],
            height=result["height"],
            thumbnail_url=f"/api/assets/{result['asset_id']}/thumbnail",
        )

    raise HTTPException(status_code=422, detail=f"Unsupported session kind: {kind!r}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session(body: CreateSessionRequest, db: DbSession) -> CreateSessionResponse:
    source_path = _resolve_source_path(body.target, db)
    session_key = uuid.uuid4().hex
    db_path = get_cache_db_path()
    init_cache_db(db_path)
    created_at = datetime.now(UTC).isoformat()
    create_edit_session(db_path, session_key, body.target.kind, body.target.id, str(source_path), created_at)
    original_preview_url = f"/api/edit-sessions/{session_key}/preview/0"
    return CreateSessionResponse(session_key=session_key, original_preview_url=original_preview_url)


@router.get("/{session_key}", response_model=SessionStateResponse)
def get_session_state(session_key: str) -> SessionStateResponse:
    db_path = get_cache_db_path()
    session = get_edit_session(db_path, session_key)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    raw_steps = get_edit_steps(db_path, session_key)
    steps = [StepInfo(seq=s["seq"], op=s["op"], params=s["params_dict"]) for s in raw_steps]
    return SessionStateResponse(
        session_key=session_key,
        kind=session["kind"],
        target_id=session["target_id"],
        steps=steps,
    )


@router.post("/{session_key}/steps", response_model=StepResponse)
async def apply_step(session_key: str, body: ApplyStepRequest) -> StepResponse:
    db_path = get_cache_db_path()
    session = get_edit_session(db_path, session_key)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    existing = get_edit_steps(db_path, session_key)
    new_seq = (existing[-1]["seq"] + 1) if existing else 1

    source_path = Path(session["source_path"])
    all_steps: list[dict[str, Any]] = [*existing, {"seq": new_seq, "op": body.op, "params_dict": body.params}]

    loop = asyncio.get_event_loop()
    try:
        preview = await loop.run_in_executor(None, _render_steps, source_path, all_steps)
    except ModelNotAvailableError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "MODEL_UNAVAILABLE", "op": exc.op, "role": exc.role},
        ) from exc

    params_json = json.dumps(body.params)
    append_edit_step(db_path, session_key, new_seq, body.op, params_json, preview)

    return StepResponse(seq=new_seq, preview_url=f"/api/edit-sessions/{session_key}/preview/{new_seq}")


@router.post("/{session_key}/rollback", response_model=RollbackResponse)
def rollback_session(session_key: str, body: RollbackRequest) -> RollbackResponse:
    db_path = get_cache_db_path()
    session = get_edit_session(db_path, session_key)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    truncate_steps_after(db_path, session_key, body.to_seq)
    return RollbackResponse(seq=body.to_seq)


@router.get("/{session_key}/preview/{seq}")
async def get_preview(session_key: str, seq: int) -> Response:
    db_path = get_cache_db_path()
    session = get_edit_session(db_path, session_key)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if seq == 0:
        source_path = Path(session["source_path"])
        loop = asyncio.get_event_loop()
        preview = await loop.run_in_executor(None, _render_steps, source_path, [])
        return Response(content=preview, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    preview = get_edit_step_preview(db_path, session_key, seq)
    if preview is None:
        raise HTTPException(status_code=404, detail="Step preview not found")
    return Response(content=preview, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/{session_key}/save", response_model=VersionDto | OrientationOverwriteDto, status_code=201)
async def save_session(
    session_key: str, body: SaveRequest, db: DbSession
) -> VersionDto | OrientationOverwriteDto:
    """Final render at original resolution, save to personX/edits/, create version row.

    Orientation-only sessions (rotate/mirror steps exclusively) skip the version
    pipeline and overwrite the source in place instead — see _save_orientation_overwrite.
    """
    cache_path = get_cache_db_path()
    session_row = get_edit_session(cache_path, session_key)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    steps = get_edit_steps(cache_path, session_key)
    if not steps:
        raise HTTPException(status_code=422, detail="No steps to save — nothing to render")

    if is_orientation_only(steps):
        return await _save_orientation_overwrite(session_row, steps, db)

    source_path = Path(session_row["source_path"])
    instance_id, face_id, parent_version_id, person_id = _resolve_save_context(session_row, db)

    loop = asyncio.get_event_loop()
    try:
        final_img = await loop.run_in_executor(None, _render_image, source_path, steps, None)
    except ModelNotAvailableError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "MODEL_UNAVAILABLE", "op": exc.op, "role": exc.role},
        ) from exc

    pil_format, ext, quality = _determine_output_format(steps, final_img)
    width, height = final_img.size

    data_root = Path(get_data_root())
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=500, detail="Person not found for version save")
    person_dir = ensure_person_folder(data_root, person)
    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)

    if body.mode == "overwrite":
        current_version = _find_current_version(db, instance_id, face_id)
        if current_version is not None:
            old_path = Path(current_version.path)
            new_path = old_path.with_suffix(f".{ext}")
            await loop.run_in_executor(None, _save_image_to_disk, final_img, new_path, pil_format, quality)
            if old_path != new_path and old_path.exists():
                old_path.unlink()
            current_version.path = str(new_path.resolve())
            current_version.type = _determine_version_type(steps)
            current_version.params = _build_version_params(steps, width, height)
            db.commit()
            db.refresh(current_version)
            await _generate_version_thumbnail(current_version.id, new_path)
            loop.run_in_executor(
                None,
                _run_version_face_dedupe,
                current_version.id,
                instance_id,
                face_id,
            )
            return _build_version_dto(current_version, width, height)

    filename = f"edit_{uuid.uuid4().hex[:12]}.{ext}"
    edit_path = edits_dir / filename
    await loop.run_in_executor(None, _save_image_to_disk, final_img, edit_path, pil_format, quality)

    _unset_current_versions(db, instance_id, face_id)

    version = Version(
        instance_id=instance_id,
        face_id=face_id,
        type=_determine_version_type(steps),
        parent_id=parent_version_id,
        path=str(edit_path.resolve()),
        is_current=True,
        params=_build_version_params(steps, width, height),
        created_at=datetime.now(UTC),
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    await _generate_version_thumbnail(version.id, edit_path)

    # Kick off Face-Dedupe as a background task (§8.3) — non-blocking
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        None,
        _run_version_face_dedupe,
        version.id,
        instance_id,
        face_id,
    )

    return _build_version_dto(version, width, height)


def _find_current_version(
    db: Session, instance_id: int | None, face_id: int | None
) -> Version | None:
    query = db.query(Version).filter(Version.is_current.is_(True))
    if instance_id is not None:
        query = query.filter(Version.instance_id == instance_id)
    else:
        query = query.filter(Version.face_id == face_id)
    return query.first()


# ── Versions router (thumbnail + file) ──────────────────────────────────────

@versions_router.get("", response_model=VersionsPage)
def list_versions(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> VersionsPage:
    """List all saved edit versions (newest first) for the gallery."""
    query = session.query(Version)
    total = query.count()
    versions: list[Version] = (
        query
        .order_by(Version.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items: list[VersionGalleryDto] = []
    for version in versions:
        parent_asset_id: int | None = None
        if version.instance_id is not None:
            instance = session.get(AssetInstance, version.instance_id)
            if instance is not None:
                parent_asset_id = instance.asset_id

        width: int | None = None
        height: int | None = None
        if version.params:
            width = version.params.get("width")
            height = version.params.get("height")

        items.append(VersionGalleryDto(
            id=version.id,
            type=version.type,
            is_current=version.is_current,
            params=version.params,
            created_at=version.created_at,
            thumbnail_url=f"/api/versions/{version.id}/thumbnail",
            parent_asset_id=parent_asset_id,
            width=width,
            height=height,
        ))

    return VersionsPage(items=items, total=total, page=page, page_size=page_size)


@versions_router.get("/{version_id}/thumbnail")
async def get_version_thumbnail(
    version_id: int,
    db: DbSession,
    size: Annotated[int, Query()] = 256,
) -> Response:
    if size not in (256, 512, 1024):
        raise HTTPException(status_code=422, detail="size must be 256, 512 or 1024")
    version = db.get(Version, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    data = await asyncio.to_thread(get_thumbnail, cache_path, version_id, size, "edit")
    if data is None:
        source = Path(version.path)
        if not source.exists():
            raise HTTPException(status_code=404, detail="Version file not found on disk")
        data = await asyncio.to_thread(generate_thumbnail, source, size)
        await asyncio.to_thread(store_thumbnail, cache_path, version_id, size, data, "edit")

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=31536000, immutable"},
    )


@versions_router.get("/{version_id}/file")
async def get_version_file(version_id: int, db: DbSession) -> FileResponse:
    version = db.get(Version, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    path = Path(version.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Version file not found on disk")
    return FileResponse(
        path,
        headers={"Cache-Control": "max-age=31536000, immutable"},
    )
