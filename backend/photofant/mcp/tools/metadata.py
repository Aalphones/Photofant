"""Write-Tools: Metadaten & Tag-Vokabular (Phase 3, non-destruktiv).

Tags/Caption/Source/Framing/Original-Zuordnung pro Foto oder Batch, plus das globale
Tag-Vokabular (umbenennen, mergen, Aliase) und ein Klassifizierungs-Rerun. Registriert an
`mcp_server` (Import in `server.py` löst die `@mcp_server.tool()`-Decorator aus — siehe
FINDINGS.md Phase 2).

Kein Tool hier ist destruktiv im Sinne des README-Kontrakts (Papierkorb/Löschen/Reparatur) —
kein Confirmation-Gate nötig. Jedes Write-Tool ruft die bestehende `api/*.py`-Endpoint-
Funktion über `adapter.run_endpoint()` auf (keine Doppel-Logik) und gibt den aktualisierten
Zustand knapp zurück, nicht den vollen DTO-Dump. Eine `HTTPException` aus dem Endpoint
(404/409/422) wird auf eine Text-Antwort für den Agenten gemappt statt hochgeworfen.
"""
from __future__ import annotations

from collections.abc import Awaitable
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from photofant.api.assets import (
    AssetPatchBody,
    PatchCaptionRequest,
    PatchTagsRequest,
    patch_asset,
    patch_asset_caption,
    patch_asset_tags,
)
from photofant.api.classify import ClassifyStep, RerunRequest
from photofant.api.classify import trigger_rerun as _trigger_rerun_endpoint
from photofant.api.tags import BulkTagRequest, MergeTagsRequest, RenameTagRequest, SetTagAliasesRequest
from photofant.api.tags import bulk_tag as _bulk_tag_endpoint
from photofant.api.tags import list_tags as _list_tags_endpoint
from photofant.api.tags import merge_tags as _merge_tags_endpoint
from photofant.api.tags import rename_tag as _rename_tag_endpoint
from photofant.api.tags import set_tag_aliases as _set_tag_aliases_endpoint
from photofant.db.models import Tag
from photofant.mcp.adapter import db_session, run_endpoint
from photofant.mcp.server import mcp_server
from photofant.settings import load_settings


async def _run_or_error[Result](coro: Awaitable[Result]) -> Result | dict[str, object]:
    """Ruft eine Endpoint-Coroutine auf; mappt eine `HTTPException` (404/409/422 aus dem
    Endpoint) auf eine Text-Antwort für den Agenten, statt sie als Python-Exception
    hochzuwerfen (Phase-3-Checkliste: „Fehler-Mapping“)."""
    try:
        return await coro
    except HTTPException as exc:
        return {"error": exc.detail, "status_code": exc.status_code}


def _count_tags(session: Session, query: str | None) -> int:
    q = session.query(func.count(Tag.id))
    if query:
        q = q.filter(Tag.name.ilike(f"%{query}%"))
    return q.scalar() or 0


@mcp_server.tool()
async def edit_tags(
    asset_id: int, add: list[str] | None = None, remove: list[int] | None = None,
) -> dict[str, object]:
    """Fügt einem Foto Tags hinzu (Namen — werden als `kind=manual` angelegt/aktualisiert)
    und/oder entfernt Tags (per Tag-ID). Gibt die neue Tag-Liste des Assets zurück."""
    body = PatchTagsRequest(add=add or [], remove=remove or [])
    result = await _run_or_error(run_endpoint(patch_asset_tags, asset_id=asset_id, body=body))
    if isinstance(result, dict):
        return result
    return {"asset_id": result.id, "tags": [tag.name for tag in result.tags]}


@mcp_server.tool()
async def bulk_edit_tags(
    asset_ids: list[int], add: list[str] | None = None, remove: list[int] | None = None,
) -> dict[str, object]:
    """Fügt Tags zu mehreren Fotos gleichzeitig hinzu/entfernt sie (wie `edit_tags`, aber für
    eine Liste von Assets). Gibt keine Tag-Liste je Asset zurück (wäre pro Foto ein Extra-Read)
    — nur eine Bestätigung mit der betroffenen Asset-Zahl."""
    body = BulkTagRequest(asset_ids=asset_ids, add=add or [], remove=remove or [])
    result = await _run_or_error(run_endpoint(_bulk_tag_endpoint, body=body))
    if isinstance(result, dict):
        return result
    return {"asset_count": len(asset_ids), "added": add or [], "removed": remove or []}


@mcp_server.tool()
async def set_caption(asset_id: int, caption: str) -> dict[str, object]:
    """Setzt die Bildunterschrift manuell — markiert sie als bearbeitet, ein automatischer
    Klassifizierungs-Rerun überschreibt sie danach nicht mehr."""
    body = PatchCaptionRequest(caption=caption)
    result = await _run_or_error(run_endpoint(patch_asset_caption, asset_id=asset_id, body=body))
    if isinstance(result, dict):
        return result
    return {"asset_id": result.id, "caption": result.caption}


@mcp_server.tool()
async def set_photo_meta(
    asset_id: int,
    source: str | None = None,
    framing: str | None = None,
    original_id: int | None = None,
    clear_original: bool = False,
) -> dict[str, object]:
    """Setzt Quelle/Framing/Original-Zuordnung eines Fotos — nur angegebene Felder ändern
    sich. `source`/`framing` weglassen lässt sie unverändert (kein Clear-Pfad nötig, beide
    sind nie sinnvoll leer). `original_id` wird nur bei Angabe gesetzt; um die Zuordnung zu
    entfernen, explizit `clear_original=true` setzen."""
    fields: dict[str, object] = {}
    if source is not None:
        fields["source"] = source
    if framing is not None:
        fields["framing"] = framing
    if clear_original:
        fields["original_id"] = None
    elif original_id is not None:
        fields["original_id"] = original_id

    body = AssetPatchBody.model_validate(fields)
    result = await _run_or_error(run_endpoint(patch_asset, asset_id=asset_id, body=body))
    if isinstance(result, dict):
        return result
    return {
        "asset_id": result.id,
        "source": result.source,
        "framing": result.framing,
        "original_id": result.original_id,
    }


@mcp_server.tool()
async def set_classification(
    asset_ids: list[int] | Literal["all"],
    steps: list[ClassifyStep] | None = None,
    caption_preset_id: int | None = None,
) -> dict[str, object]:
    """Stößt einen Klassifizierungs-Rerun an (Standard: nur `categories`) — asynchron,
    liefert eine `job_id` zum Verfolgen über `get_job_status`. `steps` kann zusätzlich
    `tags`, `caption`, `embedding`, `heuristics`, `faces` enthalten (dieselbe Pipeline wie
    ein manueller Rerun in der UI). `caption_preset_id` nur relevant, wenn `caption` in
    `steps` steht."""
    body = RerunRequest(
        asset_ids=asset_ids, steps=steps or ["categories"], caption_preset_id=caption_preset_id,
    )
    response = await _trigger_rerun_endpoint(body=body)
    return {"job_id": response.job_id}


@mcp_server.tool()
async def list_tags(query: str | None = None, page: int = 1) -> dict[str, object]:
    """Listet das Tag-Vokabular (Name, Foto-Anzahl, Aliase), optional gefiltert nach einem
    Namens-Teilstring. Gedeckelt auf `mcp.max_search_results`; `total` zählt alle zum Filter
    passenden Tags (nicht nur die aktuelle Seite)."""
    mcp_settings = load_settings().get("mcp", {})
    max_results = mcp_settings.get("max_search_results", 50)
    with db_session() as session:
        items = await _list_tags_endpoint(session=session, query=query, page=page, page_size=max_results)
        total = _count_tags(session, query)
    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": max_results,
    }


@mcp_server.tool()
async def rename_tag(tag_id: int, name: str) -> dict[str, object]:
    """Benennt einen kanonischen Tag um (muss eindeutig sein — Namenskonflikt kommt als
    Fehlertext zurück statt als Exception)."""
    body = RenameTagRequest(name=name)
    result = await _run_or_error(run_endpoint(_rename_tag_endpoint, tag_id=tag_id, body=body))
    if isinstance(result, dict):
        return result
    return result.model_dump()


@mcp_server.tool()
async def merge_tags(from_ids: list[int], into_id: int) -> dict[str, object]:
    """Merged mehrere Tags in einen kanonischen Tag — die Quell-Tags werden zu Aliasen,
    ihre Zuordnungen auf allen Fotos werden auf den Ziel-Tag umgehängt."""
    body = MergeTagsRequest(from_ids=from_ids, into_id=into_id)
    result = await _run_or_error(run_endpoint(_merge_tags_endpoint, body=body))
    if isinstance(result, dict):
        return result
    return {"into_id": into_id, "merged_from": from_ids}


@mcp_server.tool()
async def set_tag_aliases(tag_id: int, names: list[str]) -> dict[str, object]:
    """Setzt die vollständige Alias-Liste eines kanonischen Tags — Namen, die vorher als
    Alias standen und hier fehlen, werden wieder zu eigenständigen Tags."""
    body = SetTagAliasesRequest(names=names)
    result = await _run_or_error(run_endpoint(_set_tag_aliases_endpoint, tag_id=tag_id, body=body))
    if isinstance(result, dict):
        return result
    return {"tag_id": tag_id, "aliases": names}
