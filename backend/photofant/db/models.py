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
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_unknown: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    group_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
    clip_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    # P37: second, purely visual embedding (DINOv2, 768-dim) — its own vector space
    # (vec_asset_dino), independent of the SigLIP2 space above. A NULL here is a valid
    # state (asset not yet DINOv2-embedded); rerank degrades to plain SigLIP2 then.
    dino_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    caption_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")  # P6 Phase 3
    original_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("asset.id"), nullable=True, index=True,
    )  # index: migration 0023 (P21 Phase 1 — Stapel-Query)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssetInstance(Base):
    __tablename__ = "asset_instance"
    __table_args__ = (UniqueConstraint("asset_id", "person_id", name="uq_instance_asset_person"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), nullable=False)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), nullable=False, index=True)
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
    # P37: separate finish-flag for the DINOv2 embedding so a library can gain the
    # second embedding on a rerun without recomputing SigLIP2 (embedding_done stays set).
    dino_embedding_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
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
        Index("ix_asset_tag_tag_id", "tag_id"),  # DB-seitig bereits via Migration 0028 angelegt
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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # P10 Phase 1
    cover_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("asset.id"), nullable=True, index=True,
    )  # P10 Phase 1 — explizit gewähltes Cover statt nur automatischer Top-4-Vorschau


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
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # P10 Phase 1 — manuelle Reihenfolge


class Face(Base):
    __tablename__ = "face"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("asset.id"), nullable=True, index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("person.id"), nullable=True, index=True)
    source_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crop_path: Mapped[str] = mapped_column(Text, nullable=False)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    padding: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
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


class PromptTemplate(Base):
    __tablename__ = "prompt_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)



class ClassificationCategory(Base):
    __tablename__ = "classification_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)  # single | multi
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    min_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class ClassificationLabel(Base):
    __tablename__ = "classification_label"
    __table_args__ = (
        UniqueConstraint("category_id", "name", name="uq_classification_label_category_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("classification_category.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    clip_prompts: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    wd14_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


class AssetClassification(Base):
    __tablename__ = "asset_classification"

    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), primary_key=True, index=True)
    label_id: Mapped[int] = mapped_column(
        ForeignKey("classification_label.id", ondelete="CASCADE"), primary_key=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("classification_category.id"), nullable=False, index=True,
    )  # denormalisiert für Filter/Facets
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # clip | wd14 | fused


class KnowledgeEntity(Base):
    """Cache-Zeile einer Wissens-Entity (P22) — reiner Index, Wahrheit ist die Markdown-Datei.

    ``id`` ist die stabile Entity-``id`` (``<type>/<slug>``) aus dem Vault, nicht autoincrement.
    ``aliases`` liegt als JSON-Liste vor (Suche via ``cast(..., Text).like(...)``, siehe
    ``knowledge/repository.py`` — FTS ist laut Kontrakt optional, nicht Pflicht).
    """

    __tablename__ = "knowledge_entities"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, server_default="[]")  # type: ignore[type-arg]


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("knowledge_entities.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    # Entity-id des Ziels (<type>/<slug>) — keine FK: das Ziel kann angelegt werden,
    # bevor/nachdem die Beziehung geschrieben wird (Vault ist die Wahrheit, nicht die DB).
    target: Mapped[str] = mapped_column(Text, nullable=False, index=True)


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("knowledge_entities.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)


class KnowledgeMediaLink(Base):
    __tablename__ = "knowledge_media_links"
    __table_args__ = (
        UniqueConstraint("entity_id", "kind", "target_id", name="uq_knowledge_media_link"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("knowledge_entities.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # person | asset
    # person.id oder asset.id, je nach kind — keine FK, weil die Ziel-Tabelle variiert
    # (gleiches Muster wie ReviewItem.face_id).
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)


class KnowledgeTask(Base):
    """Offene „hier fehlt Wissen"-Aufgabe (P23) — Arbeitszustand, kein Vault-Wissen.

    ``context`` ist frei geformtes JSON (z.B. ``{"ref": "person/max-mustermann"}``);
    Dedup läuft über ``kind`` + ``context``-Gleichheit unter offenen Aufgaben, siehe
    ``knowledge/tasks.py::TaskService.create_task``.
    """

    __tablename__ = "knowledge_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open", index=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReviewItem(Base):
    """Review queue for both duplicate candidates and face suggestions.

    The two types share this table but have different uniqueness rules:
    - dupe_candidate rows (face_id IS NULL) are keyed on the asset pair.
    - face_suggestion rows are keyed on face_id and only while pending —
      asset_a_id/asset_b_id are both set to the same asset for these rows,
      so they can't be part of the asset-pair uniqueness (a photo with
      multiple faces would need several rows for the same asset pair).
    """

    __tablename__ = "review_item"
    __table_args__ = (
        Index(
            "uq_review_item_pair", "type", "asset_a_id", "asset_b_id",
            unique=True, sqlite_where=text("face_id IS NULL"),
        ),
        Index(
            "uq_review_item_face_pending", "face_id",
            unique=True, sqlite_where=text("type = 'face_suggestion' AND resolved_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # dupe_candidate | face_suggestion
    asset_a_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), nullable=False)
    asset_b_id: Mapped[int] = mapped_column(ForeignKey("asset.id"), nullable=False)
    clip_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    face_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suggested_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
