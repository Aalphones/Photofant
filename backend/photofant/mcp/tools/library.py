"""Read-Tools: Finden & Ansehen (Phase 2).

Suche, Detailansicht, Bild-Content, Ähnlichkeit, Ableitungs-Baum, Modell-Fähigkeiten,
Personen-Liste und Job-Verfolgung. Registriert an `mcp_server` (Import in `server.py`
löst die `@mcp_server.tool()`-Decorator aus — siehe FINDINGS.md Phase 2).

Jedes Tool ruft die bestehende `api/*.py`-Endpoint-Funktion über `adapter.run_endpoint()`
bzw. eine eigene `db_session()` auf (README-Kontrakt: keine Doppel-Logik). Ausnahme
`get_capabilities`: der Endpoint ist synchron (kein `Awaitable`), daher direkter Aufruf
statt `run_endpoint`. Die Rückgabe ist knappes, agent-lesbares JSON — keine rohen
DTO-Dumps mit Bild-Blobs; Bilder kommen ausschließlich über `view_photo`.
"""
from __future__ import annotations

from mcp.server.fastmcp import Image
from sqlalchemy.orm import Session

from photofant.api.assets import (
    SearchMode,
    SortField,
    SortOrder,
    get_asset,
    get_asset_lineage,
    get_asset_thumbnail,
    list_assets,
)
from photofant.api.models import get_capabilities as _get_capabilities_endpoint
from photofant.api.persons import list_persons as _list_persons_endpoint
from photofant.api.review import get_similar_assets
from photofant.db.models import Asset, AssetTag, Tag
from photofant.jobs.queue import JobState, JobStatus, job_queue
from photofant.mcp.adapter import db_session, run_endpoint
from photofant.mcp.server import mcp_server
from photofant.settings import load_settings

_CAPTION_PREVIEW_LENGTH = 140
_VALID_THUMBNAIL_SIZES = (256, 512, 1024)


def _shorten_caption(caption: str | None) -> str | None:
    if caption is None or len(caption) <= _CAPTION_PREVIEW_LENGTH:
        return caption
    return caption[:_CAPTION_PREVIEW_LENGTH].rstrip() + "…"


def _nearest_valid_thumbnail_size(configured_size: int) -> int:
    """`get_asset_thumbnail` akzeptiert nur {256,512,1024}; `mcp.thumbnail_size` ist aber
    ein freies Zahlenfeld (64-1024) — auf die nächstgelegene erlaubte Größe snappen."""
    return min(_VALID_THUMBNAIL_SIZES, key=lambda valid_size: abs(valid_size - configured_size))


def _batch_captions(session: Session, asset_ids: list[int]) -> dict[int, str | None]:
    if not asset_ids:
        return {}
    rows = session.query(Asset.id, Asset.caption).filter(Asset.id.in_(asset_ids)).all()
    return dict(tuple(row) for row in rows)


def _batch_tag_names(session: Session, asset_ids: list[int]) -> dict[int, list[str]]:
    if not asset_ids:
        return {}
    rows = (
        session.query(AssetTag.asset_id, Tag.name)
        .join(Tag, Tag.id == AssetTag.tag_id)
        .filter(AssetTag.asset_id.in_(asset_ids))
        .filter(AssetTag.manually_removed.is_(False))
        .all()
    )
    names_by_asset_id: dict[int, list[str]] = {}
    for asset_id, tag_name in rows:
        names_by_asset_id.setdefault(asset_id, []).append(tag_name)
    return names_by_asset_id


def _job_to_dict(status: JobStatus) -> dict[str, object]:
    return {
        "job_id": status.id,
        "kind": str(status.kind),
        "label": status.label,
        "progress": status.progress,
        "state": str(status.state),
        "error": status.error,
    }


@mcp_server.tool()
async def search_photos(
    query: str | None = None,
    mode: SearchMode = SearchMode.TAGS,
    tags: list[int] | None = None,
    person_id: int | None = None,
    classification: list[int] | None = None,
    source: list[str] | None = None,
    quality_min: float | None = None,
    framing: list[str] | None = None,
    favourite: bool | None = None,
    sort: SortField = SortField.DATE,
    order: SortOrder = SortOrder.DESC,
    page: int = 1,
    page_size: int | None = None,
) -> dict[str, object]:
    """Durchsucht die Foto-Bibliothek nach Text/Tag/Person/Klassifizierung/Qualität/Framing/Favorit.

    `query` + `mode` steuern die Textsuche: "tags" (Tag-Namen), "caption" (Bildunterschrift),
    "semantic" (CLIP-Ähnlichkeit, braucht aktives Semantik-Modell — siehe `get_capabilities`),
    "text" (Volltext über Tags/Personen/Klassifizierung/Caption). Ergebnis ist auf
    `mcp.max_search_results` gedeckelt und nennt `total` fürs Paginieren. Für den Bild-Inhalt
    danach `view_photo(asset_id)` rufen, für alle Metadaten `get_photo(asset_id)`.
    """
    mcp_settings = load_settings().get("mcp", {})
    max_results = mcp_settings.get("max_search_results", 50)
    capped_page_size = min(page_size or max_results, max_results)

    with db_session() as session:
        result = await list_assets(
            session=session,
            page=page,
            page_size=capped_page_size,
            sort=sort,
            order=order,
            favourite=favourite,
            source=source,
            quality_min=quality_min,
            tags=tags,
            classification=classification,
            person_id=person_id,
            framing=framing,
            q=query,
            q_mode=mode,
        )
        asset_ids = [item.id for item in result.items]
        captions_by_id = _batch_captions(session, asset_ids)
        tag_names_by_id = _batch_tag_names(session, asset_ids)

        items = [
            {
                "id": item.id,
                "hash": item.content_hash,
                "res": {"width": item.width, "height": item.height},
                "source": item.source,
                "caption": _shorten_caption(captions_by_id.get(item.id)),
                "tags": tag_names_by_id.get(item.id, []),
                "favourite": item.favourite,
            }
            for item in result.items
        ]
        facets = result.facets.model_dump()

    return {
        "items": items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "facets": facets,
    }


@mcp_server.tool()
async def get_photo(asset_id: int) -> dict[str, object]:
    """Liefert alle Metadaten eines Fotos: Tags, Caption, Gesichter, Versionen, Klassifizierung,
    Qualität, Framing, Pfad. Für den Bild-Inhalt selbst `view_photo(asset_id)` nutzen."""
    detail = await run_endpoint(get_asset, asset_id=asset_id)
    return detail.model_dump(mode="json")


@mcp_server.tool(structured_output=False)
async def view_photo(asset_id: int) -> Image | str:
    """Zeigt das Foto als Bild (JPEG, Kantenlänge `mcp.thumbnail_size`) — genau ein Bild pro
    Aufruf. Gibt stattdessen einen Hinweistext zurück, wenn `mcp.return_images=false`.

    `structured_output=False`: `Image` ist keine Pydantic-Klasse — ein Output-Schema-Versuch
    würde beim Tool-Registrieren mit einem Schema-Fehler crashen."""
    mcp_settings = load_settings().get("mcp", {})
    if not mcp_settings.get("return_images", True):
        return "Bild-Rückgabe ist deaktiviert (Einstellung mcp.return_images=false)."

    size = _nearest_valid_thumbnail_size(mcp_settings.get("thumbnail_size", 256))
    response = await run_endpoint(get_asset_thumbnail, asset_id=asset_id, size=size)
    return Image(data=bytes(response.body), format="jpeg")


@mcp_server.tool()
async def list_facets(
    query: str | None = None,
    mode: SearchMode = SearchMode.TAGS,
    tags: list[int] | None = None,
    person_id: int | None = None,
    classification: list[int] | None = None,
    source: list[str] | None = None,
    quality_min: float | None = None,
    framing: list[str] | None = None,
    favourite: bool | None = None,
) -> dict[str, object]:
    """Zeigt verfügbare Filter (Tags/Quellen/Framings/Klassifizierungen) mit Zählern für die
    aktuelle Such-Einschränkung — der Überblick, wonach gefiltert werden kann, ohne Foto-Items
    zu laden. Dieselben Filter-Parameter wie `search_photos`."""
    with db_session() as session:
        result = await list_assets(
            session=session,
            page=1,
            page_size=1,
            favourite=favourite,
            source=source,
            quality_min=quality_min,
            tags=tags,
            classification=classification,
            person_id=person_id,
            framing=framing,
            q=query,
            q_mode=mode,
        )
        facets = result.facets.model_dump()
    return facets


@mcp_server.tool()
async def find_similar(asset_id: int, limit: int | None = None) -> list[dict[str, object]]:
    """Findet CLIP-ähnliche Fotos zum gegebenen Asset (braucht aktives Dupe/CLIP-Modell —
    siehe `get_capabilities`). Ohne `limit` kommen alle Treffer innerhalb des konfigurierten
    Ähnlichkeits-Schwellwerts (Einstellungen → Duplikate)."""
    similar = await run_endpoint(get_similar_assets, asset_id=asset_id)
    if limit is not None:
        similar = similar[:limit]
    return [item.model_dump(mode="json") for item in similar]


@mcp_server.tool()
async def get_lineage(asset_id: int) -> dict[str, object]:
    """Ableitungs-Baum eines Fotos: Editor-Versionen der Instanz + daraus extrahierte
    Gesichter + deren eigene Editor-Versionen."""
    lineage = await run_endpoint(get_asset_lineage, asset_id=asset_id)
    return lineage.model_dump(mode="json")


@mcp_server.tool()
async def get_capabilities() -> dict[str, object]:
    """Welche Modell-Fähigkeiten gerade aktiv sind: Gesichtserkennung, Tagging, Captioning,
    Semantik-Suche, Hintergrund-Entfernung, Heavy-Captioning. Vor `mode="semantic"` bzw.
    `find_similar` prüfen, ob die passende Fähigkeit an ist."""
    with db_session() as session:
        capabilities = _get_capabilities_endpoint(session=session)
    return capabilities.model_dump()


@mcp_server.tool()
async def list_persons() -> list[dict[str, object]]:
    """Listet alle Personen mit Namen, Gruppe, Foto-Anzahl und Portrait-Gesicht-ID (nur
    Lesen — Anlegen/Umbenennen/Merge folgt in Phase 4)."""
    persons = await run_endpoint(_list_persons_endpoint)
    return [person.model_dump(mode="json") for person in persons]


@mcp_server.tool()
async def get_job_status(job_id: str) -> dict[str, object]:
    """Status/Fortschritt/Fehler eines einzelnen Hintergrund-Jobs (Import/Scan/Rerun/…) —
    zum Pollen nach einem Tool, das eine `job_id` zurückgibt."""
    for status in job_queue.snapshot():
        if status.id == job_id:
            return _job_to_dict(status)
    return {"error": f"Job {job_id} nicht gefunden."}


@mcp_server.tool()
async def list_jobs(state: JobState | None = None) -> dict[str, object]:
    """Listet laufende/fertige Hintergrund-Jobs, optional gefiltert nach Status. Gedeckelt
    auf `mcp.max_search_results`; `total` nennt die nach `state` gefilterte Gesamtzahl vor
    dem Deckel."""
    mcp_settings = load_settings().get("mcp", {})
    max_results = mcp_settings.get("max_search_results", 50)
    jobs = job_queue.snapshot()
    if state is not None:
        jobs = [job for job in jobs if job.state == state]
    total = len(jobs)
    capped_jobs = jobs[:max_results]
    return {"items": [_job_to_dict(job) for job in capped_jobs], "total": total}
