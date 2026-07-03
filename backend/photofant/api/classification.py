"""Classification CRUD — categories and labels for the WD14+CLIP fusion engine (P18).

SQLite runs without `PRAGMA foreign_keys=ON` (project-wide, see FINDINGS.md) — the
declared `ON DELETE CASCADE` on classification_label/asset_classification never fires.
Deletes here therefore remove dependent rows explicitly.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from photofant.db.models import AssetClassification, ClassificationCategory, ClassificationLabel
from photofant.db.session import get_session

log = logging.getLogger(__name__)

router = APIRouter(prefix="/classification")

DbSession = Annotated[Session, Depends(get_session)]

_VALID_MODES = frozenset({"single", "multi"})


class ClassificationLabelDto(BaseModel):
    id: int
    category_id: int
    name: str
    position: int
    clip_prompts: list[str] | None
    wd14_tags: list[str] | None


class ClassificationCategoryDto(BaseModel):
    id: int
    name: str
    mode: str
    position: int
    enabled: bool
    builtin: bool
    min_confidence: float | None
    labels: list[ClassificationLabelDto]


class CategoryCreate(BaseModel):
    name: str
    mode: str
    position: int | None = None


class CategoryPatch(BaseModel):
    name: str | None = None
    mode: str | None = None
    position: int | None = None
    enabled: bool | None = None
    min_confidence: float | None = None


class LabelCreate(BaseModel):
    name: str
    clip_prompts: list[str] | None = None
    wd14_tags: list[str] | None = None


class LabelPatch(BaseModel):
    name: str | None = None
    clip_prompts: list[str] | None = None
    wd14_tags: list[str] | None = None
    position: int | None = None


def _label_to_dto(label: ClassificationLabel) -> ClassificationLabelDto:
    return ClassificationLabelDto(
        id=label.id,
        category_id=label.category_id,
        name=label.name,
        position=label.position,
        clip_prompts=label.clip_prompts,
        wd14_tags=label.wd14_tags,
    )


def _category_to_dto(category: ClassificationCategory, labels: list[ClassificationLabel]) -> ClassificationCategoryDto:
    return ClassificationCategoryDto(
        id=category.id,
        name=category.name,
        mode=category.mode,
        position=category.position,
        enabled=category.enabled,
        builtin=category.builtin,
        min_confidence=category.min_confidence,
        labels=[_label_to_dto(label) for label in sorted(labels, key=lambda label: label.position)],
    )


def _next_category_position(session: Session) -> int:
    max_position = session.query(func.max(ClassificationCategory.position)).scalar()
    return 0 if max_position is None else max_position + 1


def _next_label_position(session: Session, category_id: int) -> int:
    max_position = (
        session.query(func.max(ClassificationLabel.position))
        .filter(ClassificationLabel.category_id == category_id)
        .scalar()
    )
    return 0 if max_position is None else max_position + 1


def _validate_mode(mode: str) -> None:
    if mode not in _VALID_MODES:
        raise HTTPException(status_code=422, detail=f"mode must be one of: {', '.join(sorted(_VALID_MODES))}")


def _delete_category_cascade(session: Session, category_id: int) -> None:
    """Remove asset_classification + labels for a category, then the category itself."""
    label_ids_sub = (
        session.query(ClassificationLabel.id)
        .filter(ClassificationLabel.category_id == category_id)
        .subquery()
    )
    session.query(AssetClassification).filter(AssetClassification.label_id.in_(label_ids_sub)).delete(
        synchronize_session=False,
    )
    session.query(ClassificationLabel).filter(ClassificationLabel.category_id == category_id).delete(
        synchronize_session=False,
    )


def _delete_label_cascade(session: Session, label_id: int) -> None:
    session.query(AssetClassification).filter(AssetClassification.label_id == label_id).delete(
        synchronize_session=False,
    )


@router.get("/categories", response_model=list[ClassificationCategoryDto])
def list_categories(session: DbSession) -> list[ClassificationCategoryDto]:
    categories = session.query(ClassificationCategory).order_by(ClassificationCategory.position).all()
    labels = session.query(ClassificationLabel).all()
    labels_by_category: dict[int, list[ClassificationLabel]] = {}
    for label in labels:
        labels_by_category.setdefault(label.category_id, []).append(label)
    return [_category_to_dto(category, labels_by_category.get(category.id, [])) for category in categories]


@router.post("/categories", response_model=ClassificationCategoryDto, status_code=201)
def create_category(body: CategoryCreate, session: DbSession) -> ClassificationCategoryDto:
    _validate_mode(body.mode)
    conflict = session.query(ClassificationCategory).filter(ClassificationCategory.name == body.name).first()
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Category name already exists")

    category = ClassificationCategory(
        name=body.name,
        mode=body.mode,
        position=body.position if body.position is not None else _next_category_position(session),
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    log.info("Created classification category %d (%s)", category.id, category.name)
    return _category_to_dto(category, [])


@router.patch("/categories/{category_id}", response_model=ClassificationCategoryDto)
def patch_category(category_id: int, body: CategoryPatch, session: DbSession) -> ClassificationCategoryDto:
    category = session.get(ClassificationCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    fields_set = body.model_fields_set
    if "mode" in fields_set and body.mode is not None:
        _validate_mode(body.mode)

    if "name" in fields_set and body.name is not None:
        conflict = (
            session.query(ClassificationCategory)
            .filter(ClassificationCategory.name == body.name, ClassificationCategory.id != category_id)
            .first()
        )
        if conflict is not None:
            raise HTTPException(status_code=409, detail="Category name already exists")
        category.name = body.name
    if "mode" in fields_set and body.mode is not None:
        category.mode = body.mode
    if "position" in fields_set and body.position is not None:
        category.position = body.position
    if "enabled" in fields_set and body.enabled is not None:
        category.enabled = body.enabled
    if "min_confidence" in fields_set:
        category.min_confidence = body.min_confidence

    session.commit()
    session.refresh(category)
    labels = session.query(ClassificationLabel).filter(ClassificationLabel.category_id == category_id).all()
    return _category_to_dto(category, labels)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, session: DbSession) -> Response:
    category = session.get(ClassificationCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    _delete_category_cascade(session, category_id)
    session.delete(category)
    session.commit()
    log.info("Deleted classification category %d (%s)", category_id, category.name)
    return Response(status_code=204)


@router.post("/categories/{category_id}/labels", response_model=ClassificationLabelDto, status_code=201)
def create_label(category_id: int, body: LabelCreate, session: DbSession) -> ClassificationLabelDto:
    category = session.get(ClassificationCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    conflict = (
        session.query(ClassificationLabel)
        .filter(ClassificationLabel.category_id == category_id, ClassificationLabel.name == body.name)
        .first()
    )
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Label name already exists in this category")

    label = ClassificationLabel(
        category_id=category_id,
        name=body.name,
        position=_next_label_position(session, category_id),
        clip_prompts=body.clip_prompts,
        wd14_tags=body.wd14_tags,
    )
    session.add(label)
    session.commit()
    session.refresh(label)
    log.info("Created classification label %d (%s) in category %d", label.id, label.name, category_id)
    return _label_to_dto(label)


@router.patch("/labels/{label_id}", response_model=ClassificationLabelDto)
def patch_label(label_id: int, body: LabelPatch, session: DbSession) -> ClassificationLabelDto:
    label = session.get(ClassificationLabel, label_id)
    if label is None:
        raise HTTPException(status_code=404, detail="Label not found")

    fields_set = body.model_fields_set
    if "name" in fields_set and body.name is not None:
        conflict = (
            session.query(ClassificationLabel)
            .filter(
                ClassificationLabel.category_id == label.category_id,
                ClassificationLabel.name == body.name,
                ClassificationLabel.id != label_id,
            )
            .first()
        )
        if conflict is not None:
            raise HTTPException(status_code=409, detail="Label name already exists in this category")
        label.name = body.name
    if "clip_prompts" in fields_set:
        label.clip_prompts = body.clip_prompts
    if "wd14_tags" in fields_set:
        label.wd14_tags = body.wd14_tags
    if "position" in fields_set and body.position is not None:
        label.position = body.position

    session.commit()
    session.refresh(label)
    return _label_to_dto(label)


@router.delete("/labels/{label_id}", status_code=204)
def delete_label(label_id: int, session: DbSession) -> Response:
    label = session.get(ClassificationLabel, label_id)
    if label is None:
        raise HTTPException(status_code=404, detail="Label not found")
    _delete_label_cascade(session, label_id)
    session.delete(label)
    session.commit()
    log.info("Deleted classification label %d (%s)", label_id, label.name)
    return Response(status_code=204)
