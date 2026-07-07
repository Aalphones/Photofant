"""Write-Tools: Personen & Faces (Phase 4).

Personen anlegen/umbenennen/gruppieren, Fotos/Gesichter zuordnen, mergen/splitten/löschen,
Face-Galerie, Matches, Neuclustering und die Face-Review-Queue. Registriert an `mcp_server`
(Import in `server.py` löst die `@mcp_server.tool()`-Decorator aus — siehe FINDINGS.md Phase 2).

Destruktive/nicht-reversible Tools (`merge_persons`, `delete_person`, `delete_face`) laufen über
`gate.confirmation_required()` — ohne `confirm=true` führen sie nichts aus, sondern geben eine
Klartext-Warnung zurück. Reversible Tools (`assign_person`, `bulk_assign_person`, `split_person`,
`resolve_face_review`) laufen ohne Gate. `list_persons` steht bereits in `tools/library.py`
(Phase 2) — hier kein Duplikat.
"""
from __future__ import annotations

from collections.abc import Awaitable
from typing import Literal

from fastapi import HTTPException

from photofant.api.assets import AssignPersonRequest
from photofant.api.assets import assign_person_to_asset as _assign_person_to_asset_endpoint
from photofant.api.faces import AssignRequest
from photofant.api.faces import assign_face as _assign_face_endpoint
from photofant.api.faces import delete_face as _delete_face_endpoint
from photofant.api.faces import get_face_matches as _get_face_matches_endpoint
from photofant.api.faces import list_faces_gallery as _list_faces_gallery_endpoint
from photofant.api.faces import trigger_clustering as _trigger_clustering_endpoint
from photofant.api.persons import (
    BulkAssignRequest,
    CreatePersonRequest,
    MergeRequest,
    SplitRequest,
    UpdatePersonRequest,
)
from photofant.api.persons import bulk_assign_to_person as _bulk_assign_to_person_endpoint
from photofant.api.persons import create_person as _create_person_endpoint
from photofant.api.persons import delete_person_endpoint as _delete_person_endpoint
from photofant.api.persons import merge_persons_endpoint as _merge_persons_endpoint
from photofant.api.persons import split_person as _split_person_endpoint
from photofant.api.persons import update_person as _update_person_endpoint
from photofant.api.review_queue import ReviewActionRequest
from photofant.api.review_queue import list_review_queue as _list_review_queue_endpoint
from photofant.api.review_queue import resolve_face_review as _resolve_face_review_endpoint
from photofant.mcp.adapter import run_endpoint
from photofant.mcp.gate import confirmation_required
from photofant.mcp.server import mcp_server
from photofant.settings import load_settings


async def _run_or_error[Result](coro: Awaitable[Result]) -> Result | dict[str, object]:
    """Ruft eine Endpoint-Coroutine auf; mappt eine `HTTPException` (404/409/422 aus dem
    Endpoint) auf eine Text-Antwort für den Agenten, statt sie als Python-Exception
    hochzuwerfen (gleiches Muster wie `tools/metadata.py`)."""
    try:
        return await coro
    except HTTPException as exc:
        return {"error": exc.detail, "status_code": exc.status_code}


@mcp_server.tool()
async def create_person(name: str, group: str | None = None) -> dict[str, object]:
    """Legt eine neue benannte Person an (Ordner wird automatisch erstellt). `group` setzt
    optional die Gruppenzugehörigkeit in einem zweiten Schritt (Endpoint kennt sie beim
    Anlegen nicht direkt)."""
    result = await _run_or_error(run_endpoint(_create_person_endpoint, body=CreatePersonRequest(name=name)))
    if isinstance(result, dict):
        return result
    if group is not None:
        grouped = await _run_or_error(
            run_endpoint(_update_person_endpoint, person_id=result.id, body=UpdatePersonRequest(group_name=group)),
        )
        if isinstance(grouped, dict):
            return grouped
        result = grouped
    return {"person_id": result.id, "name": result.name, "group": result.group_name}


@mcp_server.tool()
async def rename_person(person_id: int, name: str | None = None, group: str | None = None) -> dict[str, object]:
    """Benennt eine Person um und/oder setzt ihre Gruppe — nur angegebene Felder ändern sich.
    Weder `name` noch `group` gesetzt → Fehlertext (der Endpoint verlangt mindestens eins)."""
    body = UpdatePersonRequest(name=name, group_name=group)
    result = await _run_or_error(run_endpoint(_update_person_endpoint, person_id=person_id, body=body))
    if isinstance(result, dict):
        return result
    return {"person_id": result.id, "name": result.name, "group": result.group_name}


@mcp_server.tool()
async def assign_person(person_id: int, asset_id: int | None = None, face_id: int | None = None) -> dict[str, object]:
    """Ordnet ein Foto (`asset_id`) oder ein einzelnes Gesicht (`face_id`) einer Person zu —
    genau eins von beiden angeben. Reversibel (kein Gate): verschiebt die Datei physisch in
    den Personen-Ordner, kann jederzeit erneut umgehängt werden."""
    if (asset_id is None) == (face_id is None):
        return {"error": "Genau eins von asset_id oder face_id angeben.", "status_code": 422}
    if face_id is not None:
        face_result = await _run_or_error(
            run_endpoint(_assign_face_endpoint, face_id=face_id, body=AssignRequest(person_id=person_id)),
        )
        if isinstance(face_result, dict):
            return face_result
        return {
            "face_id": face_result.face_id,
            "asset_id": face_result.asset_id,
            "person_id": face_result.new_person_id,
        }
    asset_result = await _run_or_error(
        run_endpoint(
            _assign_person_to_asset_endpoint, asset_id=asset_id, body=AssignPersonRequest(person_id=person_id),
        ),
    )
    if isinstance(asset_result, dict):
        return asset_result
    return {
        "asset_id": asset_result.asset_id,
        "person_id": asset_result.person_id,
        "instance_id": asset_result.instance_id,
    }


@mcp_server.tool()
async def bulk_assign_person(person_id: int, asset_ids: list[int]) -> dict[str, object]:
    """Ordnet mehrere Fotos auf einmal einer Person zu — asynchron, liefert eine `job_id` zum
    Verfolgen über `get_job_status`."""
    result = await _run_or_error(
        run_endpoint(_bulk_assign_to_person_endpoint, person_id=person_id, body=BulkAssignRequest(asset_ids=asset_ids)),
    )
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


@mcp_server.tool()
async def merge_persons(from_id: int, into_id: int, confirm: bool = False) -> dict[str, object]:
    """Merged eine Person in eine andere — alle Fotos und Gesichter wandern physisch zur
    Zielperson, die Quellperson verschwindet. **Nicht umkehrbar — verlangt `confirm=true`.**"""
    action_desc = f"Person {from_id} wird in Person {into_id} gemerged (Quellperson verschwindet)"
    warning = confirmation_required(action_desc, confirm)
    if warning is not None:
        return {"warning": warning}
    body = MergeRequest(from_id=from_id, into_id=into_id)
    result = await _run_or_error(run_endpoint(_merge_persons_endpoint, body=body))
    if isinstance(result, dict):
        return result
    return {"faces_moved": result.faces_moved, "instances_moved": result.instances_moved}


@mcp_server.tool()
async def split_person(person_id: int, face_ids: list[int]) -> dict[str, object]:
    """Löst die angegebenen Gesichter aus einer Person heraus und legt dafür eine neue Person
    an — reversibel (die neue Person lässt sich jederzeit zurückmergen), daher kein Gate."""
    result = await _run_or_error(
        run_endpoint(_split_person_endpoint, person_id=person_id, body=SplitRequest(face_ids=face_ids)),
    )
    if isinstance(result, dict):
        return result
    return {
        "new_person_id": result.new_person_id,
        "faces_moved": result.faces_moved,
        "instances_created": result.instances_created,
    }


@mcp_server.tool()
async def delete_person(person_id: int, confirm: bool = False) -> dict[str, object]:
    """Löscht eine Person endgültig — ihre Fotos und Gesichter wandern zu „Unbekannt", der
    Ordner wird entfernt. **Nicht umkehrbar — verlangt `confirm=true`.**"""
    warning = confirmation_required(f"Person {person_id} wird gelöscht, ihre Fotos wandern zu „Unbekannt\"", confirm)
    if warning is not None:
        return {"warning": warning}
    result = await _run_or_error(run_endpoint(_delete_person_endpoint, person_id=person_id))
    if isinstance(result, dict):
        return result
    return {"faces_moved": result.faces_moved, "instances_moved": result.instances_moved}


@mcp_server.tool()
async def list_faces(person_id: int | None = None, page: int = 1) -> dict[str, object]:
    """Listet Gesichter aus der Face-Galerie, optional gefiltert nach Person. Gedeckelt auf
    `mcp.max_search_results`; `total` zählt alle passenden Gesichter (nicht nur die Seite)."""
    max_results = load_settings().get("mcp", {}).get("max_search_results", 50)
    page_result = await run_endpoint(
        _list_faces_gallery_endpoint, page=page, page_size=max_results, person_id=person_id, asset_ids=None,
    )
    return {
        "items": [item.model_dump(mode="json") for item in page_result.items],
        "total": page_result.total,
        "page": page_result.page,
        "page_size": page_result.page_size,
    }


@mcp_server.tool()
async def get_face_matches(face_id: int) -> dict[str, object]:
    """Top-10 disjunkte Personen-Vorschläge für ein Gesicht per Cosine-Similarity (z.B. um
    eine passende Person vor `assign_person` zu finden)."""
    result = await _run_or_error(run_endpoint(_get_face_matches_endpoint, face_id=face_id))
    if isinstance(result, dict):
        return result
    return {"matches": [match.model_dump(mode="json") for match in result]}


@mcp_server.tool()
async def delete_face(face_id: int, confirm: bool = False) -> dict[str, object]:
    """Löscht ein Gesicht endgültig (DB-Zeile, Crop-Datei, Vektor-Index-Eintrag).
    **Nicht umkehrbar — verlangt `confirm=true`.**"""
    warning = confirmation_required(f"Gesicht {face_id} wird endgültig gelöscht", confirm)
    if warning is not None:
        return {"warning": warning}
    result = await _run_or_error(run_endpoint(_delete_face_endpoint, face_id=face_id))
    if isinstance(result, dict):
        return result
    return {"face_id": face_id, "deleted": True}


@mcp_server.tool()
async def recluster() -> dict[str, object]:
    """Stößt ein initiales HDBSCAN-Neuclustering über alle Gesichts-Embeddings an —
    asynchron, liefert eine `job_id` zum Verfolgen über `get_job_status`."""
    response = await _trigger_clustering_endpoint()
    return {"job_id": response.job_id}


@mcp_server.tool()
async def list_face_review() -> dict[str, object]:
    """Listet die offenen Einträge der Face-Review-Queue (automatische Personen-Vorschläge,
    die noch bestätigt/abgelehnt/umgehängt werden müssen)."""
    items = await run_endpoint(_list_review_queue_endpoint)
    return {"items": [item.model_dump(mode="json") for item in items]}


@mcp_server.tool()
async def resolve_face_review(
    face_id: int, action: Literal["confirm", "reject", "reassign"], person_id: int | None = None,
) -> dict[str, object]:
    """Löst einen Face-Review-Eintrag auf: `confirm` übernimmt den vorgeschlagenen Match,
    `reject` schickt das Gesicht zu „Unbekannt", `reassign` hängt es auf `person_id` um
    (dafür nötig). Reversibel (kein Gate) — jede Zuordnung lässt sich per `assign_person`
    wieder ändern."""
    body = ReviewActionRequest(action=action, person_id=person_id)
    result = await _run_or_error(run_endpoint(_resolve_face_review_endpoint, face_id=face_id, body=body))
    return dict(result)
