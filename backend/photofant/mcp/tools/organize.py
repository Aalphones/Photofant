"""Write-Tools: Import, Organisieren, Duplikate (Phase 5).

Import/Scan/Verarbeitung, Papierkorb & Favoriten, Alben/Trainingssets samt Smart-Trigger,
Export und die Duplikat-Werkzeuge (Bibliotheks-Scan + personenbezogene Ad-hoc-Suche).
Registriert an `mcp_server` (Import in `server.py` löst die `@mcp_server.tool()`-Decorator
aus — siehe FINDINGS.md Phase 2).

Zwei Endpoints brauchen keine DB-Session (`trigger_rerun`, `start_dupe_scan` — beide nehmen
nur ein Request-Body-Argument) und werden deshalb direkt aufgerufen statt über
`adapter.run_endpoint()` (FINDINGS.md → Phase 3/4/5/6: sync/session-lose Endpoints).

Gate (`confirm=true` nötig): `empty_trash`, `delete_collection`, `resolve_duplicate` (nur bei
`delete_a`/`delete_b`). Alles andere ist reversibel und läuft ohne Gate.
"""
from __future__ import annotations

from collections.abc import Awaitable
from typing import Literal

from fastapi import HTTPException

from photofant.api.assets import (
    BulkTrashRequest,
    FavouriteRequest,
    ImportRequest,
)
from photofant.api.assets import (
    bulk_trash_assets as _bulk_trash_assets_endpoint,
)
from photofant.api.assets import (
    delete_asset as _delete_asset_endpoint,
)
from photofant.api.assets import (
    import_assets as _import_assets_endpoint,
)
from photofant.api.assets import (
    scan_assets as _scan_assets_endpoint,
)
from photofant.api.assets import (
    set_asset_favourite as _set_asset_favourite_endpoint,
)
from photofant.api.classify import ClassifyStep, RerunRequest
from photofant.api.classify import trigger_rerun as _trigger_rerun_endpoint
from photofant.api.collections import (
    AddItemsRequest,
    CaptionActionRequest,
    CollectionExportRequest,
    CreateCollectionRequest,
    CreateTriggerRequest,
    SidecarMode,
    UpdateCollectionRequest,
    UpdateTriggerRequest,
)
from photofant.api.collections import (
    add_items as _add_items_endpoint,
)
from photofant.api.collections import (
    add_trigger as _add_trigger_endpoint,
)
from photofant.api.collections import (
    apply_caption_action_to_set as _apply_caption_action_to_set_endpoint,
)
from photofant.api.collections import (
    create_collection as _create_collection_endpoint,
)
from photofant.api.collections import (
    delete_collection as _delete_collection_endpoint,
)
from photofant.api.collections import (
    delete_trigger as _delete_trigger_endpoint,
)
from photofant.api.collections import (
    export_collection as _export_collection_endpoint,
)
from photofant.api.collections import (
    get_training_set_stats as _get_training_set_stats_endpoint,
)
from photofant.api.collections import (
    list_collections as _list_collections_endpoint,
)
from photofant.api.collections import (
    list_triggers as _list_triggers_endpoint,
)
from photofant.api.collections import (
    remove_item as _remove_item_endpoint,
)
from photofant.api.collections import (
    update_collection as _update_collection_endpoint,
)
from photofant.api.collections import (
    update_trigger as _update_trigger_endpoint,
)
from photofant.api.duplicates import DupeSearchRequest
from photofant.api.duplicates import search_person_duplicates as _search_person_duplicates_endpoint
from photofant.api.jobs import DupeScanRequest, DupeScanScope
from photofant.api.jobs import start_dupe_scan as _start_dupe_scan_endpoint
from photofant.api.review import ResolveRequest
from photofant.api.review import list_dupe_pairs as _list_dupe_pairs_endpoint
from photofant.api.review import resolve_dupe as _resolve_dupe_endpoint
from photofant.api.trash import empty_trash as _empty_trash_endpoint
from photofant.api.trash import list_trash as _list_trash_endpoint
from photofant.api.trash import restore_asset as _restore_asset_endpoint
from photofant.collections.captions import CaptionAction
from photofant.mcp.adapter import run_endpoint
from photofant.mcp.gate import confirmation_required
from photofant.mcp.server import mcp_server
from photofant.settings import load_settings

CollectionKind = Literal["album", "smart_album", "training_set"]
MatchMode = Literal["any", "all"]
TriggerType = Literal["person", "tag", "caption"]
DupeResolution = Literal["a_is_original", "b_is_original", "delete_a", "delete_b", "dismiss"]


async def _run_or_error[Result](coro: Awaitable[Result]) -> Result | dict[str, object]:
    """Ruft eine Endpoint-Coroutine auf; mappt eine `HTTPException` (404/409/422 aus dem
    Endpoint) auf eine Text-Antwort für den Agenten, statt sie als Python-Exception
    hochzuwerfen (gleiches Muster wie `tools/persons.py`)."""
    try:
        return await coro
    except HTTPException as exc:
        return {"error": exc.detail, "status_code": exc.status_code}


def _max_results() -> int:
    return load_settings().get("mcp", {}).get("max_search_results", 50)


# ── Import & Verarbeitung ──────────────────────────────────────────────────────


@mcp_server.tool()
async def import_paths(paths: list[str]) -> dict[str, object]:
    """Importiert Fotos von Server-Pfaden (Ordner oder Dateien) — asynchron, liefert eine
    `job_id` zum Verfolgen über `get_job_status`. Kein Browser-Upload (kein Datei-Handle im
    Agent-Kontext) — nur Pfade, die der Server selbst lesen kann."""
    result = await _run_or_error(run_endpoint(_import_assets_endpoint, body=ImportRequest(paths=paths)))
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


@mcp_server.tool()
async def scan_library() -> dict[str, object]:
    """Scannt den konfigurierten Datenordner nach neuen/geänderten Dateien — asynchron,
    liefert eine `job_id`."""
    result = await _run_or_error(run_endpoint(_scan_assets_endpoint))
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


@mcp_server.tool()
async def run_processing(
    asset_ids: list[int] | Literal["all"],
    steps: list[ClassifyStep],
    caption_preset_id: int | None = None,
) -> dict[str, object]:
    """Stößt die Klassifizierungs-Pipeline für die angegebenen Fotos an (oder `"all"` für
    die ganze Bibliothek) — asynchron, liefert eine `job_id`. `steps`: tags/caption/
    embedding/faces/heuristics/categories. `caption_preset_id` nur relevant, wenn `caption`
    in `steps` steht. Der Endpoint braucht keine DB-Session (öffnet sie selbst im Job) —
    daher direkter Aufruf statt über `run_endpoint()` (FINDINGS.md Phase 3/4/5/6)."""
    body = RerunRequest(asset_ids=asset_ids, steps=steps, caption_preset_id=caption_preset_id)
    response = await _trigger_rerun_endpoint(body=body)
    return {"job_id": response.job_id}


# ── Papierkorb & Favoriten ──────────────────────────────────────────────────────


@mcp_server.tool()
async def favourite_photo(asset_id: int, value: bool) -> dict[str, object]:
    """Setzt/entfernt den Favoriten-Status eines Fotos. Reversibel — kein Gate."""
    result = await _run_or_error(
        run_endpoint(_set_asset_favourite_endpoint, asset_id=asset_id, body=FavouriteRequest(value=value)),
    )
    if isinstance(result, dict):
        return result
    return {"asset_id": result.id, "favourite": result.favourite}


@mcp_server.tool()
async def trash_photo(asset_id: int) -> dict[str, object]:
    """Wirft ein Foto in den Papierkorb (Soft-Delete) — reversibel über `restore_photo`,
    daher kein Gate."""
    result = await _run_or_error(run_endpoint(_delete_asset_endpoint, asset_id=asset_id))
    if isinstance(result, dict):
        return result
    return {"asset_id": asset_id, "trashed": True}


@mcp_server.tool()
async def bulk_trash(asset_ids: list[int]) -> dict[str, object]:
    """Wirft mehrere Fotos auf einmal in den Papierkorb — reversibel, kein Gate."""
    result = await _run_or_error(
        run_endpoint(_bulk_trash_assets_endpoint, body=BulkTrashRequest(asset_ids=asset_ids)),
    )
    if isinstance(result, dict):
        return result
    return {"asset_ids": asset_ids, "trashed": True}


@mcp_server.tool()
async def restore_photo(asset_id: int) -> dict[str, object]:
    """Holt ein Foto aus dem Papierkorb zurück."""
    result = await _run_or_error(run_endpoint(_restore_asset_endpoint, asset_id=asset_id))
    if isinstance(result, dict):
        return result
    return {"asset_id": result.id, "favourite": result.favourite}


@mcp_server.tool()
async def list_trash() -> dict[str, object]:
    """Listet die Fotos im Papierkorb. Der Endpoint kennt keine Pagination — hier auf
    `mcp.max_search_results` gedeckelt, `total` zählt alle (nicht nur die gedeckelte Seite)."""
    result = await _run_or_error(run_endpoint(_list_trash_endpoint))
    if isinstance(result, dict):
        return result
    max_results = _max_results()
    return {
        "items": [item.model_dump(mode="json") for item in result[:max_results]],
        "total": len(result),
    }


@mcp_server.tool()
async def empty_trash(confirm: bool = False) -> dict[str, object]:
    """Löscht **alle** Fotos im Papierkorb endgültig. **Nicht umkehrbar — verlangt
    `confirm=true`.**"""
    warning = confirmation_required("Der komplette Papierkorb wird endgültig geleert", confirm)
    if warning is not None:
        return {"warning": warning}
    result = await _run_or_error(run_endpoint(_empty_trash_endpoint))
    if isinstance(result, dict):
        return result
    return {"emptied": True}


# ── Alben & Trainingssets ──────────────────────────────────────────────────────


@mcp_server.tool()
async def list_collections() -> dict[str, object]:
    """Listet Alben, Smart-Alben und Trainingssets. Der Endpoint kennt keine Pagination —
    hier auf `mcp.max_search_results` gedeckelt, `total` zählt alle."""
    result = await _run_or_error(run_endpoint(_list_collections_endpoint))
    if isinstance(result, dict):
        return result
    max_results = _max_results()
    return {
        "items": [item.model_dump(mode="json") for item in result[:max_results]],
        "total": len(result),
    }


@mcp_server.tool()
async def create_collection(
    name: str, kind: CollectionKind = "album", match_mode: MatchMode = "any",
) -> dict[str, object]:
    """Legt ein neues Album/Smart-Album/Trainingsset an."""
    body = CreateCollectionRequest(name=name, kind=kind, match_mode=match_mode)
    result = await _run_or_error(run_endpoint(_create_collection_endpoint, body=body))
    if isinstance(result, dict):
        return result
    return {"collection_id": result.id, "name": result.name, "kind": result.kind}


@mcp_server.tool()
async def update_collection(
    collection_id: int,
    name: str | None = None,
    kind: CollectionKind | None = None,
    match_mode: MatchMode | None = None,
    description: str | None = None,
    cover_asset_id: int | None = None,
) -> dict[str, object]:
    """Ändert Name/Art/Match-Modus/Beschreibung/Cover einer Collection — nur angegebene
    Felder ändern sich."""
    body = UpdateCollectionRequest(
        name=name, kind=kind, match_mode=match_mode, description=description, cover_asset_id=cover_asset_id,
    )
    result = await _run_or_error(run_endpoint(_update_collection_endpoint, collection_id=collection_id, body=body))
    if isinstance(result, dict):
        return result
    return {"collection_id": result.id, "name": result.name, "kind": result.kind}


@mcp_server.tool()
async def delete_collection(collection_id: int, confirm: bool = False) -> dict[str, object]:
    """Löscht eine Collection (Album/Smart-Album/Trainingsset) samt Mitgliedschaften und
    Triggern. **Die Fotos selbst bleiben unangetastet** — nur die Collection verschwindet.
    Nicht umkehrbar — verlangt `confirm=true`."""
    warning = confirmation_required(f"Collection {collection_id} wird gelöscht", confirm)
    if warning is not None:
        return {"warning": warning}
    result = await _run_or_error(run_endpoint(_delete_collection_endpoint, collection_id=collection_id))
    if isinstance(result, dict):
        return result
    return {"collection_id": collection_id, "deleted": True}


@mcp_server.tool()
async def add_to_collection(collection_id: int, asset_ids: list[int]) -> dict[str, object]:
    """Nimmt Fotos manuell in eine Collection auf (gewinnt über Smart-Trigger-Mitgliedschaft)."""
    result = await _run_or_error(
        run_endpoint(_add_items_endpoint, collection_id=collection_id, body=AddItemsRequest(asset_ids=asset_ids)),
    )
    if isinstance(result, dict):
        return result
    return {"collection_id": collection_id, "added": len(asset_ids)}


@mcp_server.tool()
async def remove_from_collection(collection_id: int, asset_id: int) -> dict[str, object]:
    """Entfernt ein Foto aus einer Collection (Foto selbst bleibt unangetastet)."""
    result = await _run_or_error(
        run_endpoint(_remove_item_endpoint, collection_id=collection_id, asset_id=asset_id),
    )
    if isinstance(result, dict):
        return result
    return {"collection_id": collection_id, "asset_id": asset_id, "removed": True}


@mcp_server.tool()
async def manage_collection_triggers(
    collection_id: int,
    action: Literal["list", "create", "update", "delete"],
    trigger_id: int | None = None,
    trigger_type: TriggerType | None = None,
    person_id: int | None = None,
    tag_id: int | None = None,
    phrase: str | None = None,
    negate: bool = False,
) -> dict[str, object]:
    """Smart-Album-Trigger CRUD in einem Tool. `action="list"` braucht nur `collection_id`.
    `action="create"` braucht `trigger_type` (+ je nach Typ `person_id`/`tag_id`/`phrase`).
    `action="update"`/`"delete"` brauchen zusätzlich `trigger_id`. Alle Trigger-Änderungen
    stoßen eine Neubewertung der Smart-Album-Mitgliedschaft an (asynchron im Endpoint)."""
    if action == "list":
        list_result = await _run_or_error(run_endpoint(_list_triggers_endpoint, collection_id=collection_id))
        if isinstance(list_result, dict):
            return list_result
        return {"items": [item.model_dump(mode="json") for item in list_result]}

    if action == "create":
        if trigger_type is None:
            return {"error": "trigger_type ist für action='create' erforderlich", "status_code": 422}
        create_body = CreateTriggerRequest(
            type=trigger_type, person_id=person_id, tag_id=tag_id, phrase=phrase, negate=negate,
        )
        create_result = await _run_or_error(
            run_endpoint(_add_trigger_endpoint, collection_id=collection_id, body=create_body),
        )
        if isinstance(create_result, dict):
            return create_result
        return create_result.model_dump(mode="json")

    if trigger_id is None:
        return {"error": f"trigger_id ist für action='{action}' erforderlich", "status_code": 422}

    if action == "update":
        update_result = await _run_or_error(
            run_endpoint(
                _update_trigger_endpoint,
                collection_id=collection_id, trigger_id=trigger_id, body=UpdateTriggerRequest(negate=negate),
            ),
        )
        if isinstance(update_result, dict):
            return update_result
        return update_result.model_dump(mode="json")

    delete_result = await _run_or_error(
        run_endpoint(_delete_trigger_endpoint, collection_id=collection_id, trigger_id=trigger_id),
    )
    if isinstance(delete_result, dict):
        return delete_result
    return {"collection_id": collection_id, "trigger_id": trigger_id, "deleted": True}


@mcp_server.tool()
async def training_set_stats(collection_id: int) -> dict[str, object]:
    """Statistiken eines Trainingssets: Framing-/Tag-Verteilung, Qualitäts-Histogramm,
    Seitenverhältnis-Buckets, Near-Dupe-Rate."""
    result = await _run_or_error(run_endpoint(_get_training_set_stats_endpoint, collection_id=collection_id))
    if isinstance(result, dict):
        return result
    return result.model_dump(mode="json")


@mcp_server.tool()
async def training_set_captions(
    collection_id: int, action: CaptionAction, params: dict[str, str] | None = None,
) -> dict[str, object]:
    """Set-weites Caption-Werkzeug für ein Trainingsset (`trigger_word`/`prefix`/`suffix`/
    `find_replace`) — asynchron, liefert eine `job_id`. Schreibt nur den Caption-Override
    des Trainingssets, die Galerie-Caption bleibt unangetastet. `params`-Schlüssel je Action:
    `trigger_word` → `word`, `prefix`/`suffix` → `text`, `find_replace` → `find`(+`replace`)."""
    body = CaptionActionRequest(action=action, params=params or {})
    result = await _run_or_error(
        run_endpoint(_apply_caption_action_to_set_endpoint, collection_id=collection_id, body=body),
    )
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


@mcp_server.tool()
async def export_collection(
    collection_id: int,
    sidecar: SidecarMode | None = None,
    split_ratio: float | None = None,
    target_dir: str | None = None,
) -> dict[str, object]:
    """Exportiert alle Mitglieder einer Collection in einen datierten Export-Ordner —
    asynchron, liefert eine `job_id`. Trainingssets können zusätzlich Kohya-Style-Sidecar-
    Dateien (`sidecar`: tags/caption/both) und einen Train/Val-Split (`split_ratio`)
    anfordern; fehlt `split_ratio`, greift das im Trainingsset gespeicherte Setting."""
    body = CollectionExportRequest(sidecar=sidecar, split_ratio=split_ratio, target_dir=target_dir)
    result = await _run_or_error(
        run_endpoint(_export_collection_endpoint, collection_id=collection_id, body=body),
    )
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


# ── Duplikate ──────────────────────────────────────────────────────────────────


@mcp_server.tool()
async def scan_duplicates(scope: DupeScanScope, asset_ids: list[int] | None = None) -> dict[str, object]:
    """Stößt einen bibliotheksweiten (`scope="all"`) oder auf eine Auswahl beschränkten
    (`scope="selection"`, braucht `asset_ids`) Duplikat-Scan an — asynchron, liefert eine
    `job_id`. Der Endpoint braucht keine DB-Session (öffnet sie selbst im Job) — daher
    direkter Aufruf statt über `run_endpoint()` (FINDINGS.md Phase 3/4/5/6)."""
    if scope == "selection" and not asset_ids:
        return {"error": "asset_ids required when scope is 'selection'", "status_code": 422}
    body = DupeScanRequest(scope=scope, asset_ids=asset_ids)
    response = await _start_dupe_scan_endpoint(body=body)
    return {"job_id": response.job_id}


@mcp_server.tool()
async def list_duplicates(offset: int = 0, limit: int | None = None) -> dict[str, object]:
    """Listet offene Duplikat-Paare aus der Review-Queue, sortiert nach CLIP-Distanz
    (ähnlichstes zuerst). `limit` fehlt → `mcp.max_search_results`."""
    effective_limit = limit if limit is not None else _max_results()
    result = await _run_or_error(
        run_endpoint(_list_dupe_pairs_endpoint, offset=offset, limit=effective_limit),
    )
    if isinstance(result, dict):
        return result
    return {
        "items": [item.model_dump(mode="json") for item in result.items],
        "total": result.total,
    }


@mcp_server.tool()
async def resolve_duplicate(
    pair_id: int, resolution: DupeResolution, confirm: bool = False,
) -> dict[str, object]:
    """Löst ein Duplikat-Paar auf: `a_is_original`/`b_is_original` setzt die Original-
    Zuordnung, `dismiss` verwirft den Vorschlag — alle drei reversibel, kein Gate.
    `delete_a`/`delete_b` wirft die entsprechende Seite in den Papierkorb — **nicht
    umkehrbar, verlangt `confirm=true`**."""
    if resolution in ("delete_a", "delete_b"):
        action_desc = f"Duplikat-Paar {pair_id}: {resolution} wirft ein Foto in den Papierkorb"
        warning = confirmation_required(action_desc, confirm)
        if warning is not None:
            return {"warning": warning}
    result = await _run_or_error(
        run_endpoint(_resolve_dupe_endpoint, item_id=pair_id, body=ResolveRequest(resolution=resolution)),
    )
    if isinstance(result, dict):
        return result
    return {"pair_id": result.id, "resolution": resolution}


@mcp_server.tool()
async def find_person_duplicates(person_id: int, clip_threshold: float | None = None) -> dict[str, object]:
    """Ad-hoc-Duplikatsuche innerhalb der Fotos einer Person per CLIP-Similarity (ohne
    vorherigen Scan). `clip_threshold` fehlt → globale Einstellung `dupe_clip_threshold`."""
    body = DupeSearchRequest(person_id=person_id, clip_threshold=clip_threshold)
    result = await _run_or_error(run_endpoint(_search_person_duplicates_endpoint, body=body))
    if isinstance(result, dict):
        return result
    return {"items": [item.model_dump(mode="json") for item in result]}
