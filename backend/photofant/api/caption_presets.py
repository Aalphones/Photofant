"""CRUD for caption presets — named, reusable captioner configs (§12.6).

A preset's `config` is validated against the `caption_mode` of its bound model
(or the default `task_token` mode when the preset is model-agnostic). Setting a
preset as default clears the previous default within the same model scope.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.db.models import CaptionPreset, ModelRegistry
from photofant.db.session import get_session
from photofant.inference.caption_config import CaptionConfigError, CaptionMode, validate_caption_config

log = logging.getLogger(__name__)

router = APIRouter(prefix="/caption-presets")

DbSession = Annotated[Session, Depends(get_session)]


class CaptionPresetDto(BaseModel):
    id: int
    name: str
    model_id: int | None
    config: dict[str, Any]
    is_default: bool


class CaptionPresetCreate(BaseModel):
    name: str
    model_id: int | None = None
    config: dict[str, Any]
    is_default: bool = False


class CaptionPresetUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool | None = None


def _to_dto(preset: CaptionPreset) -> CaptionPresetDto:
    return CaptionPresetDto(
        id=preset.id,
        name=preset.name,
        model_id=preset.model_id,
        config=preset.config,
        is_default=preset.is_default,
    )


def _caption_mode_for(session: Session, model_id: int | None) -> str:
    """Resolve the caption_mode a config must satisfy.

    Model-agnostic presets (model_id is None) default to task_token — the only
    mode with a shipped captioner today.
    """
    if model_id is None:
        return CaptionMode.TASK_TOKEN
    model = session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=422, detail={"code": "MODEL_NOT_FOUND"})
    if model.caption_mode is None:
        raise HTTPException(status_code=422, detail={"code": "NOT_A_CAPTIONER"})
    return model.caption_mode


def _validate_or_422(caption_mode: str, config: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_caption_config(caption_mode, config)
    except CaptionConfigError as error:
        raise HTTPException(status_code=422, detail={"code": error.code, "message": error.message}) from error


def _clear_other_defaults(session: Session, model_id: int | None, keep_id: int | None) -> None:
    query = session.query(CaptionPreset).filter(CaptionPreset.is_default.is_(True))
    if model_id is None:
        query = query.filter(CaptionPreset.model_id.is_(None))
    else:
        query = query.filter(CaptionPreset.model_id == model_id)
    for other in query.all():
        if other.id != keep_id:
            other.is_default = False


@router.get("", response_model=list[CaptionPresetDto])
def list_caption_presets(session: DbSession, model_id: int | None = None) -> list[CaptionPresetDto]:
    query = session.query(CaptionPreset)
    if model_id is not None:
        query = query.filter(CaptionPreset.model_id == model_id)
    return [_to_dto(preset) for preset in query.order_by(CaptionPreset.id).all()]


@router.post("", response_model=CaptionPresetDto, status_code=201)
def create_caption_preset(body: CaptionPresetCreate, session: DbSession) -> CaptionPresetDto:
    caption_mode = _caption_mode_for(session, body.model_id)
    normalized_config = _validate_or_422(caption_mode, body.config)

    preset = CaptionPreset(
        name=body.name,
        model_id=body.model_id,
        config=normalized_config,
        is_default=body.is_default,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(preset)
    session.flush()
    if body.is_default:
        _clear_other_defaults(session, body.model_id, keep_id=preset.id)
    session.commit()
    session.refresh(preset)
    log.info("Created caption preset %d (%s)", preset.id, preset.name)
    return _to_dto(preset)


@router.patch("/{preset_id}", response_model=CaptionPresetDto)
def update_caption_preset(preset_id: int, body: CaptionPresetUpdate, session: DbSession) -> CaptionPresetDto:
    preset = session.get(CaptionPreset, preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail={"code": "PRESET_NOT_FOUND"})

    if body.name is not None:
        preset.name = body.name

    if body.config is not None:
        caption_mode = _caption_mode_for(session, preset.model_id)
        preset.config = _validate_or_422(caption_mode, body.config)

    if body.is_default is not None:
        preset.is_default = body.is_default
        if body.is_default:
            _clear_other_defaults(session, preset.model_id, keep_id=preset.id)

    session.commit()
    session.refresh(preset)
    return _to_dto(preset)


@router.delete("/{preset_id}", status_code=204)
def delete_caption_preset(preset_id: int, session: DbSession) -> None:
    preset = session.get(CaptionPreset, preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail={"code": "PRESET_NOT_FOUND"})
    session.delete(preset)
    session.commit()
    log.info("Deleted caption preset %d", preset_id)
