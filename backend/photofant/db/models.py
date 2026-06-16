from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, Text, UniqueConstraint
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
    caption_preset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FK added in P4
    tagger: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    clip_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
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
    classified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
