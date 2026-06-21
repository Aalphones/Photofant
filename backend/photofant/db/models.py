from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_unknown: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")


class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str | None] = mapped_column(Text, nullable=True)
    framing: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    captioner: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_preset_id: Mapped[int | None] = mapped_column(
        ForeignKey("caption_preset.id"), nullable=True
    )
    tagger: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    clip_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    caption_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")  # P6 Phase 3
    phash: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("asset.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssetInstance(Base):
    __tablename__ = "asset_instance"
    __table_args__ = (UniqueConstraint("asset_id", "person_id", name="uq_instance_asset_person"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), nullable=False)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    favourite: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    fixed_person: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    missing_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProcessingLedger(Base):
    __tablename__ = "processing_ledger"

    content_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    faces_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    tags_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    caption_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    embedding_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    heuristics_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    classified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manifest_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    variant: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    components: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    managed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    caption_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)  # lowercase + underscores (canonical)
    alias_of: Mapped[int | None] = mapped_column(ForeignKey("tag.id"), nullable=True, index=True)  # P6 Phase 3


class AssetTag(Base):
    __tablename__ = "asset_tag"
    __table_args__ = (
        UniqueConstraint("asset_id", "tag_id", name="uq_asset_tag"),
        Index("ix_asset_tag_asset_id", "asset_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default="auto")  # auto | manual
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    manually_removed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")  # P6 Phase 3


class CaptionPreset(Base):
    __tablename__ = "caption_preset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("model_registry.id"), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # type: ignore[type-arg]
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Collection(Base):
    __tablename__ = "collection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # album | training_set | smart_album
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default="album")
    match_mode: Mapped[str] = mapped_column(Text, nullable=False, server_default="any")  # smart_album: any | all
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]


class SmartTrigger(Base):
    __tablename__ = "smart_trigger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collection.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # person | tag | caption
    person_id: Mapped[int | None] = mapped_column(ForeignKey("person.id"), nullable=True)
    tag_id: Mapped[int | None] = mapped_column(ForeignKey("tag.id"), nullable=True)
    phrase: Mapped[str | None] = mapped_column(Text, nullable=True)
    negate: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")


class CollectionItem(Base):
    __tablename__ = "collection_item"

    collection_id: Mapped[int] = mapped_column(ForeignKey("collection.id"), primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), primary_key=True, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")  # manual | smart
    caption_override: Mapped[str | None] = mapped_column(Text, nullable=True)


class Face(Base):
    __tablename__ = "face"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("asset.id"), nullable=True, index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("person.id"), nullable=True, index=True)
    source_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crop_path: Mapped[str] = mapped_column(Text, nullable=False)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    padding: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    phash: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin: Mapped[str | None] = mapped_column(Text, nullable=True)   # derived | manual_original
    origin_type: Mapped[str | None] = mapped_column(Text, nullable=True)  # original | upscale | flux_edit
    is_upscaled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    resolution: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Version(Base):
    __tablename__ = "version"
    __table_args__ = (
        CheckConstraint(
            "(instance_id IS NOT NULL AND face_id IS NULL) OR (instance_id IS NULL AND face_id IS NOT NULL)",
            name="ck_version_xor",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("asset_instance.id"), nullable=True, index=True)
    face_id: Mapped[int | None] = mapped_column(ForeignKey("face.id"), nullable=True, index=True)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("version.id"), nullable=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ComfyUIWorkflow(Base):
    __tablename__ = "comfyui_workflow"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, server_default="generic")
    template_path: Mapped[str] = mapped_column(Text, nullable=False)
    inputs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, server_default="[]")  # type: ignore[type-arg]
    params: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, server_default="[]")  # type: ignore[type-arg]
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    validation_errors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReviewItem(Base):
    __tablename__ = "review_item"
    __table_args__ = (
        UniqueConstraint("type", "asset_a_id", "asset_b_id", name="uq_review_item_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # dupe_candidate | face_suggestion
    asset_a_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), nullable=False)
    asset_b_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), nullable=False)
    phash_distance: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    face_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suggested_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
