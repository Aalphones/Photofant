"""Edit-Session API — CPU-only image editor (P8 Phase 1)

POST /edit-sessions                      → create session, returns session_key
GET  /edit-sessions/{key}                → session state + step list
POST /edit-sessions/{key}/steps          → apply op, store step preview
POST /edit-sessions/{key}/rollback       → truncate steps after to_seq
GET  /edit-sessions/{key}/preview/{seq}  → JPEG (seq=0 → original preview)
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.db.cache import (
    append_edit_step,
    create_edit_session,
    get_cache_db_path,
    get_edit_session,
    get_edit_step_preview,
    get_edit_steps,
    init_cache_db,
    truncate_steps_after,
)
from photofant.db.models import Asset, AssetInstance, Face
from photofant.db.session import get_session

log = logging.getLogger(__name__)

router = APIRouter(prefix="/edit-sessions")

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


# ── Render pipeline ───────────────────────────────────────────────────────────

def _apply_op(img: Image.Image, op: str, params: dict[str, Any]) -> Image.Image:  # type: ignore[type-arg]
    if op == "rotate":
        direction = str(params.get("dir", "cw"))
        angles: dict[str, float] = {"cw": -90.0, "ccw": 90.0, "180": 180.0}
        angle = angles.get(direction, -90.0)
        return img.rotate(angle, expand=True)

    if op == "mirror":
        axis = str(params.get("axis", "h"))
        transpose = Image.Transpose.FLIP_LEFT_RIGHT if axis == "h" else Image.Transpose.FLIP_TOP_BOTTOM
        return img.transpose(transpose)

    if op == "pad":
        width, height = img.size
        target = max(width, height)
        padded = Image.new("RGB", (target, target), (0, 0, 0))
        padded.paste(img, ((target - width) // 2, (target - height) // 2))
        return padded

    if op == "convert":
        # Format change is a save-time concern; for preview we just ensure RGB
        return img.convert("RGB")

    if op == "crop":
        # Params: x, y, w, h as percentages of the image
        x_pct = float(params.get("x", 0))
        y_pct = float(params.get("y", 0))
        w_pct = float(params.get("w", 100))
        h_pct = float(params.get("h", 100))
        img_w, img_h = img.size
        left = int(x_pct / 100 * img_w)
        top = int(y_pct / 100 * img_h)
        right = min(img_w, left + int(w_pct / 100 * img_w))
        bottom = min(img_h, top + int(h_pct / 100 * img_h))
        if right <= left or bottom <= top:
            return img
        return img.crop((left, top, right, bottom))

    if op == "smart_crop":
        # Phase 3 — stub returns image unchanged
        return img

    log.warning("Unknown op %r — returning image unchanged", op)
    return img


def _render_steps(source_path: Path, steps: list[dict[str, Any]], preview_max: int = _PREVIEW_MAX_PX) -> bytes:  # type: ignore[type-arg]
    """Apply all steps to the original image and return JPEG bytes."""
    try:
        with Image.open(source_path) as raw:
            img: Image.Image = ImageOps.exif_transpose(raw) or raw
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGB")
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                alpha = img.split()[3]
                background.paste(img, mask=alpha)
                img = background
            elif img.mode == "L":
                img = img.convert("RGB")
            img.thumbnail((preview_max, preview_max), Image.Resampling.LANCZOS)
            for step in steps:
                img = _apply_op(img, step["op"], step["params_dict"])
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"Cannot render image: {exc}") from exc
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_PREVIEW_JPEG_QUALITY)
    return buf.getvalue()


# ── Path resolution ───────────────────────────────────────────────────────────

def _resolve_source_path(target: EditTarget, db: Session) -> Path:
    """Map target (kind, id) to a readable file path."""
    if target.kind == "instance":
        # For Phase 1 we accept asset.id and resolve the first active instance
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

    raise HTTPException(status_code=422, detail=f"Unsupported target kind: {target.kind!r}")


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
    preview = await loop.run_in_executor(None, _render_steps, source_path, all_steps)

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
