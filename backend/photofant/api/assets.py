from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import tempfile
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Query as OrmQuery
from sqlalchemy.orm import Session

from photofant.config import get_data_root
from photofant.db import vector_index
from photofant.db.cache import get_cache_db_path, get_thumbnail, init_cache_db, store_thumbnail
from photofant.db.models import Asset, AssetInstance, AssetTag, CollectionItem, Face, Person, Tag, Version
from photofant.db.session import get_session
from photofant.jobs.collections_job import enqueue_reevaluate_assets
from photofant.jobs.import_job import enqueue_import, enqueue_scan
from photofant.media import moves
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)

router = APIRouter(prefix="/assets")

DbSession = Annotated[Session, Depends(get_session)]

_VALID_THUMB_SIZES = frozenset({256, 512, 1024})


class SortField(StrEnum):
    DATE = "date"
    SIZE = "size"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class SearchMode(StrEnum):
    TAGS = "tags"
    CAPTION = "caption"
    SEMANTIC = "semantic"


class AssetDto(BaseModel):
    id: int
    content_hash: str
    width: int | None
    height: int | None
    file_size: int | None
    format: str | None
    source: str | None
    created_at: datetime | None
    imported_at: datetime | None
    favourite: bool
    version_count: int
    generation_meta: dict | None  # type: ignore[type-arg]
    has_phash: bool


class TagDto(BaseModel):
    id: int
    name: str
    kind: str
    score: float | None


class FaceDto(BaseModel):
    id: int
    asset_id: int | None
    person_id: int | None
    person_name: str | None = None
    crop_url: str
    score: float | None
    age: int | None
    bbox: dict | None  # type: ignore[type-arg]
    origin: str | None
    is_upscaled: bool


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


class AssetDetailDto(AssetDto):
    path: str | None
    tags: list[TagDto]
    tagger: str | None
    caption: str | None
    captioner: str | None
    caption_preset_id: int | None
    faces: list[FaceDto] = []
    versions: list[VersionDto] = []


class FacetItem(BaseModel):
    value: str
    count: int


class TagFacetItem(BaseModel):
    id: int
    name: str
    count: int


class Facets(BaseModel):
    sources: list[FacetItem]
    tags_top: list[TagFacetItem]
    framings: list[FacetItem] = []


class AssetsPage(BaseModel):
    items: list[AssetDto]
    total: int
    page: int
    page_size: int
    facets: Facets


class ImportRequest(BaseModel):
    paths: list[str]


class JobStarted(BaseModel):
    job_id: str


class FavouriteRequest(BaseModel):
    value: bool


class PatchTagsRequest(BaseModel):
    add: list[str]   # tag names → upsert as kind=manual
    remove: list[int]  # tag IDs to remove from this asset


class PatchCaptionRequest(BaseModel):
    caption: str


def build_asset_dto(asset: Asset, instance: AssetInstance, version_count: int = 0) -> AssetDto:
    return AssetDto(
        id=asset.id,
        content_hash=asset.content_hash,
        width=asset.width,
        height=asset.height,
        file_size=asset.file_size,
        format=asset.format,
        source=asset.source,
        created_at=asset.created_at,
        imported_at=asset.imported_at,
        favourite=instance.favourite,
        version_count=version_count,
        generation_meta=asset.generation_meta,
        has_phash=asset.phash is not None,
    )


def _load_asset_tags(session: Session, asset_id: int) -> list[TagDto]:
    rows = (
        session.query(AssetTag, Tag)
        .join(Tag, Tag.id == AssetTag.tag_id)
        .filter(AssetTag.asset_id == asset_id)
        .filter(AssetTag.manually_removed.is_(False))
        .order_by(AssetTag.score.desc().nulls_last())
        .all()
    )
    return [TagDto(id=tag.id, name=tag.name, kind=asset_tag.kind, score=asset_tag.score)
            for asset_tag, tag in rows]


def _base_query(session: Session) -> OrmQuery[Any]:
    return (
        session.query(Asset, AssetInstance)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(AssetInstance.deleted_at.is_(None))
    )


def _active_row(session: Session, asset_id: int) -> tuple[Asset, AssetInstance] | None:
    return _base_query(session).filter(Asset.id == asset_id).first()


def _empty_facets() -> Facets:
    return Facets(sources=[], tags_top=[])


async def _embed_semantic(query: str) -> np.ndarray:
    """Embed *query* via CLIP text encoder. Raises 409 if model unavailable."""
    from photofant.inference.adapters.clip import resolve_clip_embedder

    embedder = resolve_clip_embedder()
    if embedder is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "SEMANTIC_SEARCH_UNAVAILABLE", "message": "CLIP-Modell ist nicht aktiv."},
        )
    return await asyncio.to_thread(embedder.embed_text, query)


def _compute_facets(session: Session, filtered: OrmQuery[Any]) -> Facets:
    src_rows = (
        filtered
        .with_entities(Asset.source, func.count(Asset.id).label("cnt"))
        .group_by(Asset.source)
        .all()
    )
    sources = [
        FacetItem(value=row.source, count=row.cnt)
        for row in src_rows
        if row.source is not None
    ]

    asset_id_sub = filtered.with_entities(Asset.id).subquery()
    tag_rows = (
        session.query(Tag.id, Tag.name, func.count(AssetTag.id).label("cnt"))
        .join(AssetTag, AssetTag.tag_id == Tag.id)
        .filter(AssetTag.asset_id.in_(asset_id_sub))
        .group_by(Tag.id, Tag.name)
        .order_by(func.count(AssetTag.id).desc())
        .limit(30)
        .all()
    )
    tags_top = [TagFacetItem(id=row.id, name=row.name, count=row.cnt) for row in tag_rows]

    framing_rows = (
        filtered
        .with_entities(Asset.framing, func.count(Asset.id).label("cnt"))
        .group_by(Asset.framing)
        .all()
    )
    framings = [
        FacetItem(value=row.framing, count=row.cnt)
        for row in framing_rows
        if row.framing is not None
    ]

    return Facets(sources=sources, tags_top=tags_top, framings=framings)


@router.get("", response_model=AssetsPage)
async def list_assets(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    sort: SortField = SortField.DATE,
    order: SortOrder = SortOrder.DESC,
    favourite: bool | None = None,
    source: Annotated[list[str] | None, Query()] = None,
    quality_min: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    tags: Annotated[list[int] | None, Query()] = None,
    collection_id: int | None = None,
    person_id: int | None = None,
    framing: Annotated[list[str] | None, Query()] = None,
    q: str | None = None,
    q_mode: SearchMode = SearchMode.TAGS,
) -> AssetsPage:
    query = _base_query(session)

    if favourite is not None:
        query = query.filter(AssetInstance.favourite.is_(favourite))
    if source:
        query = query.filter(Asset.source.in_(source))
    if person_id is not None:
        query = query.filter(AssetInstance.person_id == person_id)
    if framing:
        query = query.filter(Asset.framing.in_(framing))
    if collection_id is not None:
        collection_sub = (
            session.query(CollectionItem.asset_id)
            .filter(CollectionItem.collection_id == collection_id)
            .subquery()
        )
        query = query.filter(Asset.id.in_(collection_sub))
    if quality_min is not None and quality_min > 0.0:
        query = query.filter(Asset.quality_score >= quality_min)
    for tag_id in (tags or []):
        # Include aliases that point to this canonical tag
        alias_ids_sub = session.query(Tag.id).filter(Tag.alias_of == tag_id).subquery()
        tag_sub = (
            session.query(AssetTag.asset_id)
            .filter(
                AssetTag.manually_removed.is_(False),
                or_(AssetTag.tag_id == tag_id, AssetTag.tag_id.in_(alias_ids_sub)),
            )
            .subquery()
        )
        query = query.filter(Asset.id.in_(tag_sub))

    # Text / semantic search
    semantic_score_map: dict[int, float] = {}
    q_clean = (q or "").strip()
    if q_clean:
        if q_mode == SearchMode.TAGS:
            # Matching tag IDs (by name)
            matching_tag_ids = session.query(Tag.id).filter(Tag.name.ilike(f"%{q_clean}%")).subquery()
            # Also include tags that are aliases of any matching tag
            alias_of_matching = session.query(Tag.id).filter(Tag.alias_of.in_(matching_tag_ids)).subquery()
            name_sub = (
                session.query(AssetTag.asset_id)
                .filter(
                    AssetTag.manually_removed.is_(False),
                    or_(
                        AssetTag.tag_id.in_(matching_tag_ids),
                        AssetTag.tag_id.in_(alias_of_matching),
                    ),
                )
                .subquery()
            )
            query = query.filter(Asset.id.in_(name_sub))
        elif q_mode == SearchMode.CAPTION:
            query = query.filter(Asset.caption.ilike(f"%{q_clean}%"))
        elif q_mode == SearchMode.SEMANTIC:
            query_embedding = await _embed_semantic(q_clean)
            candidates = vector_index.search(session, query_embedding, limit=200)
            if not candidates:
                return AssetsPage(items=[], total=0, page=page, page_size=page_size, facets=_empty_facets())
            candidate_ids = [asset_id for asset_id, _ in candidates]
            semantic_score_map = dict(candidates)
            query = query.filter(Asset.id.in_(candidate_ids))

    facets = _compute_facets(session, query)
    total: int
    items: list[AssetDto]

    if semantic_score_map:
        all_rows: list[tuple[Asset, AssetInstance]] = query.all()

        def _by_score(row: tuple[Asset, AssetInstance]) -> float:
            return semantic_score_map.get(row[0].id, 0.0)

        all_rows.sort(key=_by_score, reverse=True)
        total = len(all_rows)
        start = (page - 1) * page_size
        page_rows = all_rows[start : start + page_size]
    else:
        total = query.count()
        sort_col: Any
        if sort == SortField.DATE:
            sort_col = func.coalesce(Asset.created_at, Asset.imported_at)
        else:
            sort_col = Asset.file_size
        order_fn = asc if order == SortOrder.ASC else desc
        page_rows = query.order_by(order_fn(sort_col)).offset((page - 1) * page_size).limit(page_size).all()

    version_counts = _batch_version_counts(session, [inst.id for _, inst in page_rows])
    items = [
        build_asset_dto(asset, instance, version_counts.get(instance.id, 0))
        for asset, instance in page_rows
    ]
    return AssetsPage(items=items, total=total, page=page, page_size=page_size, facets=facets)


@router.get("/{asset_id}/thumbnail")
async def get_asset_thumbnail(
    asset_id: int,
    session: DbSession,
    size: Annotated[int, Query()] = 256,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
) -> Response:
    if size not in _VALID_THUMB_SIZES:
        raise HTTPException(status_code=422, detail="size must be 256, 512 or 1024")

    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    etag = f'"{asset.content_hash}-{size}"'

    if if_none_match == etag:
        return Response(status_code=304)

    db_path = get_cache_db_path()
    init_cache_db(db_path)
    data = await asyncio.to_thread(get_thumbnail, db_path, asset.id, size)

    if data is None:
        source_path = Path(instance.path)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Source file not found on disk")
        data = await asyncio.to_thread(generate_thumbnail, source_path, size)
        await asyncio.to_thread(store_thumbnail, db_path, asset.id, size, data)

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "ETag": etag,
            "Cache-Control": "max-age=31536000, immutable",
        },
    )


@router.get("/{asset_id}/file")
async def get_asset_file(asset_id: int, session: DbSession) -> FileResponse:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    _, instance = row
    source_path = Path(instance.path)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found on disk")

    return FileResponse(
        source_path,
        headers={"Cache-Control": "max-age=31536000, immutable"},
    )


def _batch_version_counts(session: Session, instance_ids: list[int]) -> dict[int, int]:
    if not instance_ids:
        return {}
    rows = (
        session.query(Version.instance_id, func.count(Version.id))
        .filter(Version.instance_id.in_(instance_ids))
        .group_by(Version.instance_id)
        .all()
    )
    return {int(instance_id): int(count) for instance_id, count in rows}


def _load_asset_versions(session: Session, instance_id: int, asset_id: int) -> list[VersionDto]:
    instance_versions = (
        session.query(Version)
        .filter(Version.instance_id == instance_id)
        .order_by(Version.created_at.asc())
        .all()
    )
    face_ids = [
        face_id for (face_id,) in
        session.query(Face.id).filter(Face.asset_id == asset_id).all()
    ]
    face_versions: list[Version] = []
    if face_ids:
        face_versions = (
            session.query(Version)
            .filter(Version.face_id.in_(face_ids))
            .order_by(Version.created_at.asc())
            .all()
        )
    all_versions = instance_versions + face_versions
    result: list[VersionDto] = []
    for version in all_versions:
        params = version.params or {}
        width = params.get("width")
        height = params.get("height")
        res = ResDto(width=width, height=height) if width and height else None
        result.append(VersionDto(
            id=version.id,
            type=version.type,
            parent_id=version.parent_id,
            path=version.path,
            is_current=version.is_current,
            params=version.params,
            created_at=version.created_at,
            res=res,
            thumbnail_url=f"/api/versions/{version.id}/thumbnail",
        ))
    return result


def _load_asset_faces(session: Session, asset_id: int) -> list[FaceDto]:
    rows = session.query(Face).filter(Face.asset_id == asset_id).all()
    person_ids = {face.person_id for face in rows if face.person_id is not None}
    person_names: dict[int, str] = {}
    if person_ids:
        persons = session.query(Person).filter(Person.id.in_(person_ids)).all()
        person_names = {p.id: p.name for p in persons if p.name is not None}
    return [
        FaceDto(
            id=face.id,
            asset_id=face.asset_id,
            person_id=face.person_id,
            person_name=person_names.get(face.person_id) if face.person_id is not None else None,
            crop_url=f"/faces/{face.id}/thumbnail",
            score=face.score,
            age=face.age,
            bbox=face.bbox,
            origin=face.origin,
            is_upscaled=face.is_upscaled,
        )
        for face in rows
    ]


@router.get("/{asset_id}", response_model=AssetDetailDto)
async def get_asset(asset_id: int, session: DbSession) -> AssetDetailDto:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    version_count = (
        session.query(func.count(Version.id))
        .filter(Version.instance_id == instance.id)
        .scalar()
    ) or 0
    base = build_asset_dto(asset, instance, version_count)
    tags = _load_asset_tags(session, asset.id)
    faces = _load_asset_faces(session, asset.id)
    versions = _load_asset_versions(session, instance.id, asset.id)
    return AssetDetailDto(
        **base.model_dump(),
        path=instance.path,
        tags=tags,
        tagger=asset.tagger,
        caption=asset.caption,
        captioner=asset.captioner,
        caption_preset_id=asset.caption_preset_id,
        faces=faces,
        versions=versions,
    )


@router.post("/upload", response_model=JobStarted)
async def upload_assets(files: Annotated[list[UploadFile], File()]) -> JobStarted:
    """Accept multipart uploads from the browser, save to a temp dir, enqueue import."""
    if not files:
        raise HTTPException(status_code=422, detail="No files provided")

    tmp_dir = Path(tempfile.mkdtemp(prefix="pf_upload_"))
    saved: list[str] = []
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
        dest = tmp_dir / (upload.filename or f"upload{suffix}")
        content = await upload.read()
        dest.write_bytes(content)
        saved.append(str(dest))

    status = await enqueue_import(saved)
    return JobStarted(job_id=status.id)


@router.post("/import", response_model=JobStarted)
async def import_assets(body: ImportRequest, session: DbSession) -> JobStarted:
    if not body.paths:
        raise HTTPException(status_code=422, detail="paths must not be empty")
    status = await enqueue_import(body.paths)
    return JobStarted(job_id=status.id)


@router.post("/scan", response_model=JobStarted)
async def scan_assets(session: DbSession) -> JobStarted:
    data_root = get_data_root()
    status = await enqueue_scan(Path(data_root))
    return JobStarted(job_id=status.id)


@router.patch("/{asset_id}/favourite", response_model=AssetDto)
async def set_asset_favourite(asset_id: int, body: FavouriteRequest, session: DbSession) -> AssetDto:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    await moves.set_favourite(session, instance, body.value)
    return build_asset_dto(asset, instance)


@router.patch("/{asset_id}/tags", response_model=AssetDetailDto)
async def patch_asset_tags(asset_id: int, body: PatchTagsRequest, session: DbSession) -> AssetDetailDto:
    """Add/remove tags manually on a single asset."""
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset, instance = row

    for name in body.add:
        normalized = name.strip().lower().replace(" ", "_")
        if not normalized:
            continue
        tag = session.query(Tag).filter_by(name=normalized).first()
        if tag is None:
            tag = Tag(name=normalized)
            session.add(tag)
            session.flush()
        # Resolve to canonical if alias
        if tag.alias_of is not None:
            canonical = session.get(Tag, tag.alias_of)
            if canonical is not None:
                tag = canonical

        existing = session.query(AssetTag).filter_by(asset_id=asset_id, tag_id=tag.id).first()
        if existing is None:
            session.add(AssetTag(asset_id=asset_id, tag_id=tag.id, kind="manual"))
        else:
            existing.kind = "manual"
            existing.manually_removed = False

    for tag_id in body.remove:
        existing = session.query(AssetTag).filter_by(asset_id=asset_id, tag_id=tag_id).first()
        if existing is None:
            continue
        if existing.kind == "manual":
            session.delete(existing)
        else:
            # Auto tag: soft-remove so the tagger won't re-add it on rerun
            existing.manually_removed = True

    session.commit()
    session.refresh(asset)
    log.info("patch_asset_tags: asset %d +%d -%d", asset_id, len(body.add), len(body.remove))

    # Tags changed → re-evaluate this asset against every smart album (Konzept §10.1)
    await enqueue_reevaluate_assets([asset_id])
    base = build_asset_dto(asset, instance)
    tags = _load_asset_tags(session, asset.id)
    return AssetDetailDto(
        **base.model_dump(),
        path=instance.path,
        tags=tags,
        tagger=asset.tagger,
        caption=asset.caption,
        captioner=asset.captioner,
        caption_preset_id=asset.caption_preset_id,
    )


@router.patch("/{asset_id}/caption", response_model=AssetDetailDto)
async def patch_asset_caption(asset_id: int, body: PatchCaptionRequest, session: DbSession) -> AssetDetailDto:
    """Manually edit the caption; marks it as user-edited so reruns won't overwrite it."""
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset, instance = row

    asset.caption = body.caption
    asset.caption_edited = True
    session.commit()
    session.refresh(asset)
    log.info("patch_asset_caption: asset %d", asset_id)

    # Caption changed → re-evaluate this asset against every smart album (Konzept §10.1)
    await enqueue_reevaluate_assets([asset_id])
    base = build_asset_dto(asset, instance)
    tags = _load_asset_tags(session, asset.id)
    return AssetDetailDto(
        **base.model_dump(),
        path=instance.path,
        tags=tags,
        tagger=asset.tagger,
        caption=asset.caption,
        captioner=asset.captioner,
        caption_preset_id=asset.caption_preset_id,
    )


class SetOriginalRequest(BaseModel):
    original_id: int | None


@router.patch("/{asset_id}/original", response_model=AssetDto)
async def set_asset_original(asset_id: int, body: SetOriginalRequest, session: DbSession) -> AssetDto:
    """Set (or clear) asset.original_id — used by the Lightbox ad-hoc compare."""
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset, instance = row
    asset.original_id = body.original_id
    session.commit()
    session.refresh(asset)
    return build_asset_dto(asset, instance)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: int, session: DbSession) -> Response:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    _, instance = row
    data_root = get_data_root()
    await moves.soft_delete(session, instance, data_root)
    return Response(status_code=204)


# ── Versioning endpoints ──────────────────────────────────────────────────────


class SetCurrentRequest(BaseModel):
    version_id: int


@router.post("/{asset_id}/set-current", response_model=VersionDto)
async def set_current_version(asset_id: int, body: SetCurrentRequest, session: DbSession) -> VersionDto:
    """Switch the active version pointer. Gallery/Lightbox follow is_current."""
    version = session.get(Version, body.version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    _, instance = row

    if version.instance_id is not None and version.instance_id != instance.id:
        raise HTTPException(status_code=422, detail="Version does not belong to this asset's instance")
    if version.face_id is not None:
        face = session.get(Face, version.face_id)
        if face is None or face.asset_id != asset_id:
            raise HTTPException(status_code=422, detail="Version's face does not belong to this asset")

    siblings = (
        session.query(Version)
        .filter(Version.is_current.is_(True))
    )
    if version.instance_id is not None:
        siblings = siblings.filter(Version.instance_id == version.instance_id)
    else:
        siblings = siblings.filter(Version.face_id == version.face_id)
    for sibling in siblings.all():
        sibling.is_current = False

    version.is_current = True
    session.commit()
    session.refresh(version)

    params = version.params or {}
    width = params.get("width")
    height = params.get("height")
    res = ResDto(width=width, height=height) if width and height else None
    return VersionDto(
        id=version.id,
        type=version.type,
        parent_id=version.parent_id,
        path=version.path,
        is_current=version.is_current,
        params=version.params,
        created_at=version.created_at,
        res=res,
        thumbnail_url=f"/api/versions/{version.id}/thumbnail",
    )


class VersionImportResponse(BaseModel):
    version: VersionDto


@router.post("/{asset_id}/versions/import", response_model=VersionImportResponse, status_code=201)
async def import_as_version(
    asset_id: int,
    session: DbSession,
    file: UploadFile = File(...),
) -> VersionImportResponse:
    """Import an external file as a new version of this asset."""
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    _, instance = row

    person = session.get(Person, instance.person_id)
    if person is None:
        raise HTTPException(status_code=500, detail="Person not found")

    from photofant.media.person_folders import ensure_person_folder

    data_root_path = Path(get_data_root())
    person_dir = ensure_person_folder(data_root_path, person)
    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)

    import uuid as _uuid
    original_name = Path(file.filename or "import.jpg")
    ext = original_name.suffix.lower() or ".jpg"
    filename = f"import_{_uuid.uuid4().hex[:12]}{ext}"
    dest = edits_dir / filename

    content = await file.read()
    dest.write_bytes(content)

    from PIL import Image as _Image
    try:
        with _Image.open(dest) as img:
            width, height = img.size
    except Exception:
        width, height = None, None

    siblings = (
        session.query(Version)
        .filter(Version.instance_id == instance.id, Version.is_current.is_(True))
    )
    for sibling in siblings.all():
        sibling.is_current = False

    from datetime import UTC as _UTC
    from datetime import datetime as _datetime
    version = Version(
        instance_id=instance.id,
        face_id=None,
        type="import",
        parent_id=None,
        path=str(dest.resolve()),
        is_current=True,
        params={"width": width, "height": height, "source": "re-import"},
        created_at=_datetime.now(_UTC),
    )
    session.add(version)
    session.commit()
    session.refresh(version)

    from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
    from photofant.media.thumbnails import generate_thumbnail

    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for thumb_size in (256, 512):
        thumb = await asyncio.to_thread(generate_thumbnail, dest, thumb_size)
        await asyncio.to_thread(store_thumbnail, cache_path, version.id, thumb_size, thumb, "edit")

    res = ResDto(width=width, height=height) if width and height else None
    version_dto = VersionDto(
        id=version.id,
        type=version.type,
        parent_id=version.parent_id,
        path=version.path,
        is_current=version.is_current,
        params=version.params,
        created_at=version.created_at,
        res=res,
        thumbnail_url=f"/api/versions/{version.id}/thumbnail",
    )
    return VersionImportResponse(version=version_dto)


class BulkTrashRequest(BaseModel):
    asset_ids: list[int]


@router.post("/bulk-trash", status_code=204)
async def bulk_trash_assets(body: BulkTrashRequest, session: DbSession) -> Response:
    """Soft-delete a selection of assets (moves them to trash)."""
    if not body.asset_ids:
        raise HTTPException(status_code=422, detail="asset_ids must not be empty")
    data_root = get_data_root()
    for asset_id in body.asset_ids:
        row = _active_row(session, asset_id)
        if row is None:
            continue
        _, instance = row
        await moves.soft_delete(session, instance, data_root)
    return Response(status_code=204)


class BulkEditRequest(BaseModel):
    asset_ids: list[int]
    op: str
    params: dict[str, Any]  # type: ignore[type-arg]


@router.post("/{asset_id}/reveal", status_code=204)
async def reveal_asset(asset_id: int, session: DbSession) -> Response:
    """Open the asset's file in the system file browser, with the file selected."""
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    _, instance = row
    file_path = Path(instance.path)

    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(file_path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(file_path)])
    else:
        subprocess.Popen(["xdg-open", str(file_path.parent)])

    return Response(status_code=204)


@router.post("/bulk-edit", response_model=JobStarted, status_code=202)
async def bulk_edit_assets(body: BulkEditRequest) -> JobStarted:
    """Apply one op to a selection of assets — creates a new Version per asset as a Queue-Job."""
    if not body.asset_ids:
        raise HTTPException(status_code=422, detail="asset_ids must not be empty")
    _ALLOWED_BULK_OPS = frozenset({"rotate", "mirror", "convert", "rembg"})
    if body.op not in _ALLOWED_BULK_OPS:
        raise HTTPException(status_code=422, detail=f"op must be one of: {', '.join(sorted(_ALLOWED_BULK_OPS))}")

    from photofant.jobs.bulk_edit_job import enqueue_bulk_edit
    status = await enqueue_bulk_edit(body.asset_ids, body.op, body.params)
    return JobStarted(job_id=status.id)
