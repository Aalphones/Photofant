from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from rapidfuzz import fuzz
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
_VALID_FRAMINGS = frozenset({"close_up", "medium", "full_body"})
# Fuzzy-Score-Schwelle (rapidfuzz, 0-100) fuer q_mode=text — ADR-015.
# fuzz.ratio fuer Tag-/Personen-Namen, fuzz.partial_ratio fuer Captions (siehe _text_score).
_TEXT_FUZZY_THRESHOLD = 60


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
    TEXT = "text"


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
    # P21 — Stapel (Original + Editor-Dialog-Versionen + ComfyUI-original_id-Kinder):
    kind: str = "asset"  # "asset" | "version" — pseudo-entry for a version row
    version_id: int | None = None  # set when kind == "version"
    stack_size: int = 1  # 1 = kein Stapel, kein Icon
    stack_group_id: int | None = None  # gemeinsame ID über alle Mitglieder einer Gruppe


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


class AssetSummaryDto(BaseModel):
    id: int
    thumbnail_url: str
    source: str | None
    width: int | None
    height: int | None
    created_at: datetime | None


class AssetDetailDto(AssetDto):
    path: str | None
    tags: list[TagDto]
    tagger: str | None
    caption: str | None
    captioner: str | None
    caption_preset_id: int | None
    faces: list[FaceDto] = []
    versions: list[VersionDto] = []
    original_id: int | None = None
    linked_edits: list[AssetSummaryDto] = []
    quality: float | None = None
    framing: str | None = None


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


def build_asset_dto(
    asset: Asset,
    instance: AssetInstance,
    version_count: int = 0,
    *,
    stack_size: int = 1,
    stack_group_id: int | None = None,
) -> AssetDto:
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
        stack_size=stack_size,
        stack_group_id=stack_group_id,
    )


def _build_version_pseudo_dto(
    version: Version,
    instance: AssetInstance,
    asset: Asset,
    *,
    stack_size: int,
    stack_group_id: int | None,
) -> AssetDto:
    """A version row (Editor-Dialog-Edit) shown as its own gallery entry (P21).

    Identity/tag/caption fields come from the *original* asset (versions have none of
    their own) — only `created_at` and dimensions are the version's own, since editing
    can change them (crop/rotate).
    """
    params = version.params or {}
    width = params.get("width") or asset.width
    height = params.get("height") or asset.height
    return AssetDto(
        id=asset.id,
        content_hash=asset.content_hash,
        width=width,
        height=height,
        file_size=None,
        format=asset.format,
        source=asset.source,
        created_at=version.created_at,
        imported_at=asset.imported_at,
        favourite=instance.favourite,
        version_count=0,
        generation_meta=asset.generation_meta,
        has_phash=asset.phash is not None,
        kind="version",
        version_id=version.id,
        stack_size=stack_size,
        stack_group_id=stack_group_id,
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


# ── Stapel (P21 / ADR-012) ─────────────────────────────────────────────────────
#
# Eine Gruppe = Original + alle Editor-Dialog-Versionen seiner asset_instance +
# alle Assets mit original_id == Original.id (ComfyUI-Edits, ADR-013) + deren
# eigene Editor-Dialog-Versionen. Single-hop: original_id-Ketten über zwei Ebenen
# (Edit eines Edits) werden nicht rekursiv aufgelöst — seltener Fall, außerhalb
# des P21-Scopes (flaches Stapel-Modell laut README).


def _stack_roots(session: Session, asset_ids: set[int]) -> dict[int, int]:
    """Resolve each asset id to its stack root (top of the original_id chain)."""
    if not asset_ids:
        return {}
    known: dict[int, int | None] = {}
    frontier = set(asset_ids)
    for _ in range(5):  # bounded depth guard against cycles/unexpectedly deep chains
        missing = frontier - known.keys()
        if not missing:
            break
        rows = session.query(Asset.id, Asset.original_id).filter(Asset.id.in_(missing)).all()
        for asset_id, original_id in rows:
            known[asset_id] = original_id
        frontier = {oid for oid in known.values() if oid is not None} - known.keys()

    roots: dict[int, int] = {}
    for asset_id in asset_ids:
        current = asset_id
        seen: set[int] = set()
        while True:
            parent = known.get(current)
            if parent is None or current in seen:
                break
            seen.add(current)
            current = parent
        roots[asset_id] = current
    return roots


def _stack_sizes_for_roots(session: Session, roots: set[int]) -> dict[int, int]:
    """Member count per stack root: root + its original_id-children + all their versions."""
    if not roots:
        return {}

    members_by_root: dict[int, list[int]] = {root: [root] for root in roots}
    for original_id, child_id in session.query(Asset.original_id, Asset.id).filter(Asset.original_id.in_(roots)).all():
        members_by_root[original_id].append(child_id)

    all_member_ids = {member for members in members_by_root.values() for member in members}
    instance_ids_by_asset: dict[int, list[int]] = {}
    for asset_id, instance_id in (
        session.query(AssetInstance.asset_id, AssetInstance.id)
        .filter(AssetInstance.asset_id.in_(all_member_ids), AssetInstance.deleted_at.is_(None))
        .all()
    ):
        instance_ids_by_asset.setdefault(asset_id, []).append(instance_id)

    all_instance_ids = [iid for ids in instance_ids_by_asset.values() for iid in ids]
    version_counts_by_instance: dict[int, int] = {}
    if all_instance_ids:
        version_counts_by_instance = {
            int(instance_id): int(count)
            for instance_id, count in (
                session.query(Version.instance_id, func.count(Version.id))
                .filter(Version.instance_id.in_(all_instance_ids), Version.face_id.is_(None))
                .group_by(Version.instance_id)
                .all()
            )
        }

    sizes: dict[int, int] = {}
    for root, members in members_by_root.items():
        size = len(members)
        for member_id in members:
            for instance_id in instance_ids_by_asset.get(member_id, []):
                size += version_counts_by_instance.get(instance_id, 0)
        sizes[root] = size
    return sizes


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


@dataclass
class _GalleryEntry:
    """One row of the merged Fotos-Galerie result — a real Asset or a Version-Pseudo-Eintrag."""

    kind: str  # "asset" | "version"
    asset: Asset
    instance: AssetInstance
    version: Version | None = None
    sort_key: Any = None


def _version_candidates_query(session: Session, filtered: OrmQuery[Any]) -> OrmQuery[Any]:
    """Editor-Dialog-Version rows belonging to instances that already pass *filtered*.

    Reuses the caller's filter predicates (person/source/tags/caption/…) via the
    already-filtered instance set instead of re-implementing every filter for Version.
    """
    instance_ids_sub = filtered.with_entities(AssetInstance.id).scalar_subquery()
    return (
        session.query(Version, AssetInstance, Asset)
        .join(AssetInstance, AssetInstance.id == Version.instance_id)
        .join(Asset, Asset.id == AssetInstance.asset_id)
        .filter(Version.face_id.is_(None))
        .filter(Version.instance_id.in_(instance_ids_sub))
    )


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
    has_faces: bool | None = None,
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
    if has_faces is not None:
        # Extrahierte Gesichter hängen direkt am Original-Asset (Face.asset_id) —
        # unabhängig vom ProcessingLedger-Flag, das nur "Extraktion schon gelaufen"
        # markiert, nicht "es existieren noch Face-Zeilen" (z.B. nach manuellem
        # Löschen in der Review-Queue).
        face_asset_ids_sub = session.query(Face.asset_id).filter(Face.asset_id.isnot(None)).subquery()
        if has_faces:
            query = query.filter(Asset.id.in_(face_asset_ids_sub))
        else:
            query = query.filter(Asset.id.notin_(face_asset_ids_sub))
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
    score_map: dict[int, float] = {}
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
            score_map = dict(candidates)
            query = query.filter(Asset.id.in_(candidate_ids))
        elif q_mode == SearchMode.TEXT:
            # Fuzzy-Freitextsuche über Tag-Name + Caption + Personen-Name (ADR-015, Option A).
            # Kandidaten kommen bewusst aus `query` (bereits durch alle vorigen Filter
            # eingeschränkt) statt aus der Gesamtbibliothek — das ist der im ADR dokumentierte
            # 🟡-Fallback, hier von Anfang an so gebaut statt erst ab einer Schwelle zuzuschalten.
            candidate_pairs = query.with_entities(Asset.id, AssetInstance.person_id).all()
            candidate_ids = sorted({asset_id for asset_id, _ in candidate_pairs})
            if not candidate_ids:
                return AssetsPage(items=[], total=0, page=page, page_size=page_size, facets=_empty_facets())

            # (kind, text) statt nur text: Captions brauchen einen anderen Scorer als kurze
            # Tag-/Personen-Namen (siehe _text_score unten).
            candidate_texts: dict[int, list[tuple[str, str]]] = {asset_id: [] for asset_id in candidate_ids}

            for asset_id, caption in (
                session.query(Asset.id, Asset.caption)
                .filter(Asset.id.in_(candidate_ids), Asset.caption.isnot(None))
                .all()
            ):
                if caption:
                    candidate_texts[asset_id].append(("caption", caption))

            for asset_id, tag_name in (
                session.query(AssetTag.asset_id, Tag.name)
                .join(Tag, Tag.id == AssetTag.tag_id)
                .filter(AssetTag.asset_id.in_(candidate_ids), AssetTag.manually_removed.is_(False))
                .all()
            ):
                candidate_texts[asset_id].append(("tag", tag_name))

            person_ids = {person_id for _, person_id in candidate_pairs if person_id is not None}
            person_names: dict[int, str] = {}
            if person_ids:
                person_names = {
                    person_id: name
                    for person_id, name in (
                        session.query(Person.id, Person.name)
                        .filter(Person.id.in_(person_ids), Person.is_unknown.is_(False))
                        .all()
                    )
                    if name is not None
                }
            for asset_id, person_id in candidate_pairs:
                name = person_names.get(person_id) if person_id is not None else None
                if name:
                    candidate_texts[asset_id].append(("person", name))

            def _text_score(kind: str, text: str) -> float:
                # Kurze Tag-/Personen-Namen: volle String-Ähnlichkeit (fuzz.ratio). WRatio
                # matcht bei kurzen Kandidaten gegen lange/unpassende Suchbegriffe zu oft per
                # Teil-Alignment (getestet: "zzzzznonexistentqueryxyz" traf "nose" mit 67.5) —
                # ein reiner Ratio-Vergleich vermeidet diese False Positives, toleriert aber
                # weiterhin einzelne Tippfehler (z.B. "black_hiar" ./. "black_hair" -> 90).
                # Captions: partial_ratio, weil die Eingabe nur ein Wort/Fragment eines langen
                # Freitexts sein darf (Substring-artiges Matching, ebenfalls tippfehlertolerant).
                if kind == "caption":
                    return fuzz.partial_ratio(q_clean, text)
                return fuzz.ratio(q_clean, text)

            for asset_id, texts in candidate_texts.items():
                if not texts:
                    continue
                best = max(_text_score(kind, text) for kind, text in texts)
                if best >= _TEXT_FUZZY_THRESHOLD:
                    score_map[asset_id] = best

            if not score_map:
                return AssetsPage(items=[], total=0, page=page, page_size=page_size, facets=_empty_facets())
            query = query.filter(Asset.id.in_(score_map.keys()))

    facets = _compute_facets(session, query)
    version_query = _version_candidates_query(session, query)

    total = query.count() + version_query.count()

    if score_map:
        # Version-Pseudo-Einträge übernehmen den Score des Original-Assets (kein eigener
        # Embedding-Vektor/Fuzzy-Match) — siehe README: Filter/Suche greifen bei ihnen über
        # das Original. Gilt für beide score-basierten Modi (semantic + text).
        asset_rows = query.all()
        version_rows = version_query.all()
        entries = [
            _GalleryEntry(
                kind="asset", asset=asset, instance=instance,
                sort_key=score_map.get(asset.id, 0.0),
            )
            for asset, instance in asset_rows
        ] + [
            _GalleryEntry(
                kind="version", asset=asset, instance=instance, version=version,
                sort_key=score_map.get(asset.id, 0.0),
            )
            for version, instance, asset in version_rows
        ]
        entries.sort(key=lambda entry: entry.sort_key, reverse=True)
        start = (page - 1) * page_size
        page_entries = entries[start : start + page_size]
    else:
        # Merge-Strategie statt Full-Table-Fetch: die Top `fetch_limit` aus JEDEM Teilstream
        # (Assets, Versionen) reichen aus, um die angefragte Seite korrekt zu bestimmen —
        # kein Kandidat außerhalb der Top-`fetch_limit` seines eigenen Streams kann im
        # kombinierten Ranking vor Seite `page` landen (Performance-Vorgabe phase-1-Checkliste).
        fetch_limit = page * page_size
        order_fn = asc if order == SortOrder.ASC else desc

        if sort == SortField.DATE:
            asset_sort_col = func.coalesce(Asset.created_at, Asset.imported_at)
            version_sort_col = Version.created_at
        else:
            asset_sort_col = Asset.file_size
            version_sort_col = Asset.file_size  # eine Version hat keine eigene Dateigröße

        asset_rows = query.order_by(order_fn(asset_sort_col)).limit(fetch_limit).all()
        version_rows = version_query.order_by(order_fn(version_sort_col)).limit(fetch_limit).all()

        def _asset_sort_value(asset: Asset) -> Any:
            return (asset.created_at or asset.imported_at) if sort == SortField.DATE else asset.file_size

        entries = [
            _GalleryEntry(kind="asset", asset=asset, instance=instance, sort_key=_asset_sort_value(asset))
            for asset, instance in asset_rows
        ] + [
            _GalleryEntry(
                kind="version", asset=asset, instance=instance, version=version,
                sort_key=(version.created_at if sort == SortField.DATE else asset.file_size),
            )
            for version, instance, asset in version_rows
        ]
        reverse = order == SortOrder.DESC
        entries.sort(key=lambda entry: (entry.sort_key is None, entry.sort_key), reverse=reverse)
        start = (page - 1) * page_size
        page_entries = entries[start : start + page_size]

    # Stapel-Metadaten (P21)
    asset_ids_on_page = {entry.asset.id for entry in page_entries}
    roots = _stack_roots(session, asset_ids_on_page)
    stack_sizes = _stack_sizes_for_roots(session, set(roots.values()))

    version_counts = _batch_version_counts(
        session, [entry.instance.id for entry in page_entries if entry.kind == "asset"],
    )

    items: list[AssetDto] = []
    for entry in page_entries:
        root = roots.get(entry.asset.id, entry.asset.id)
        size = stack_sizes.get(root, 1)
        group_id = root if size > 1 else None
        if entry.kind == "asset":
            items.append(build_asset_dto(
                entry.asset, entry.instance, version_counts.get(entry.instance.id, 0),
                stack_size=size, stack_group_id=group_id,
            ))
        else:
            assert entry.version is not None
            items.append(_build_version_pseudo_dto(
                entry.version, entry.instance, entry.asset,
                stack_size=size, stack_group_id=group_id,
            ))

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


def _version_to_dto(version: Version) -> VersionDto:
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
    return [_version_to_dto(version) for version in instance_versions + face_versions]


def _load_face_versions(session: Session, face_id: int) -> list[VersionDto]:
    versions = (
        session.query(Version)
        .filter(Version.face_id == face_id)
        .order_by(Version.created_at.asc())
        .all()
    )
    return [_version_to_dto(version) for version in versions]


class LineageFaceDto(BaseModel):
    id: int
    person_id: int | None
    person_name: str | None
    crop_url: str
    origin: str | None
    source_version_id: int | None
    versions: list[VersionDto]


class LineageDto(BaseModel):
    asset_id: int
    thumbnail_url: str
    versions: list[VersionDto]  # Editor-Bearbeitungen der Instanz (version.instance_id)
    faces: list[LineageFaceDto]  # aus diesem Asset extrahierte Gesichter + deren eigene Edits


def _load_lineage_faces(session: Session, asset_id: int) -> list[LineageFaceDto]:
    faces = session.query(Face).filter(Face.asset_id == asset_id).order_by(Face.created_at.asc()).all()
    person_ids = {face.person_id for face in faces if face.person_id is not None}
    person_names: dict[int, str] = {}
    if person_ids:
        persons = session.query(Person).filter(Person.id.in_(person_ids)).all()
        person_names = {p.id: p.name for p in persons if p.name is not None}
    return [
        LineageFaceDto(
            id=face.id,
            person_id=face.person_id,
            person_name=person_names.get(face.person_id) if face.person_id is not None else None,
            crop_url=f"/faces/{face.id}/thumbnail",
            origin=face.origin,
            source_version_id=face.source_version_id,
            versions=_load_face_versions(session, face.id),
        )
        for face in faces
    ]


def _build_lineage_dto(session: Session, asset: Asset, instance: AssetInstance) -> LineageDto:
    instance_versions = (
        session.query(Version)
        .filter(Version.instance_id == instance.id)
        .order_by(Version.created_at.asc())
        .all()
    )
    return LineageDto(
        asset_id=asset.id,
        thumbnail_url=f"/api/assets/{asset.id}/thumbnail",
        versions=[_version_to_dto(version) for version in instance_versions],
        faces=_load_lineage_faces(session, asset.id),
    )


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


def _load_linked_edits(session: Session, asset_id: int) -> list[AssetSummaryDto]:
    """Assets whose original_id points back at *asset_id* (excludes soft-deleted)."""
    rows = _base_query(session).filter(Asset.original_id == asset_id).all()
    return [
        AssetSummaryDto(
            id=edit.id,
            thumbnail_url=f"/api/assets/{edit.id}/thumbnail",
            source=edit.source,
            width=edit.width,
            height=edit.height,
            created_at=edit.created_at,
        )
        for edit, _instance in rows
    ]


def _build_asset_detail_dto(session: Session, asset: Asset, instance: AssetInstance) -> AssetDetailDto:
    version_count = (
        session.query(func.count(Version.id))
        .filter(Version.instance_id == instance.id)
        .scalar()
    ) or 0
    base = build_asset_dto(asset, instance, version_count)
    tags = _load_asset_tags(session, asset.id)
    faces = _load_asset_faces(session, asset.id)
    versions = _load_asset_versions(session, instance.id, asset.id)
    linked_edits = _load_linked_edits(session, asset.id)
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
        original_id=asset.original_id,
        linked_edits=linked_edits,
        quality=asset.quality_score,
        framing=asset.framing,
    )


@router.get("/{asset_id}", response_model=AssetDetailDto)
async def get_asset(asset_id: int, session: DbSession) -> AssetDetailDto:
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset, instance = row
    return _build_asset_detail_dto(session, asset, instance)


@router.get("/{asset_id}/lineage", response_model=LineageDto)
async def get_asset_lineage(asset_id: int, session: DbSession) -> LineageDto:
    """Ableitungs-Baum: Original → Editor-Versionen → daraus extrahierte Gesichter → deren
    eigene Editor-Versionen (Konzept §10 Gruppierung „Original/Face/Edit", P10 Phase 1)."""
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset, instance = row
    return _build_lineage_dto(session, asset, instance)


class AssetPatchBody(BaseModel):
    source: str | None = None
    framing: str | None = None
    original_id: int | None = None


@router.patch("/{asset_id}", response_model=AssetDetailDto)
async def patch_asset(asset_id: int, body: AssetPatchBody, session: DbSession) -> AssetDetailDto:
    """Partially update source/framing/original_id — only fields present in the body are touched.

    `original_id: null` clears the assignment; omitting the field leaves it unchanged
    (distinguished via `model_fields_set`, not the value itself).
    """
    row = _active_row(session, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset, instance = row

    fields_set = body.model_fields_set
    if "framing" in fields_set and body.framing is not None and body.framing not in _VALID_FRAMINGS:
        raise HTTPException(
            status_code=422,
            detail=f"framing must be one of: {', '.join(sorted(_VALID_FRAMINGS))}",
        )

    if "source" in fields_set:
        asset.source = body.source
    if "framing" in fields_set:
        asset.framing = body.framing
    if "original_id" in fields_set:
        asset.original_id = body.original_id

    session.commit()
    session.refresh(asset)
    log.info("patch_asset: asset %d fields=%s", asset_id, sorted(fields_set))
    return _build_asset_detail_dto(session, asset, instance)


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


class AssignPersonRequest(BaseModel):
    person_id: int


class AssetPersonAssignResultDto(BaseModel):
    asset_id: int
    person_id: int
    instance_id: int


@router.patch("/{asset_id}/assign-person", response_model=AssetPersonAssignResultDto)
async def assign_person_to_asset(
    asset_id: int, body: AssignPersonRequest, session: DbSession,
) -> AssetPersonAssignResultDto:
    """Manually assign a person to an asset that has no face to reassign.

    Reuses the same physical move/copy logic as face reassignment
    (`materialize_assignment`) — works for assets without any extracted face.
    """
    from photofant.media.person_folders import materialize_assignment

    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    person = session.get(Person, body.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    data_root = get_data_root()
    instance = await asyncio.to_thread(
        materialize_assignment, session, asset_id, body.person_id, data_root, fixed=True,
    )
    if instance is None:
        raise HTTPException(
            status_code=500,
            detail=f"Could not assign asset {asset_id} to person {body.person_id} — file missing or IO error",
        )

    session.commit()
    log.info("assign_person_to_asset: asset %d → person %d", asset_id, body.person_id)

    await enqueue_reevaluate_assets([asset_id])

    return AssetPersonAssignResultDto(
        asset_id=asset_id,
        person_id=body.person_id,
        instance_id=instance.id,
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
