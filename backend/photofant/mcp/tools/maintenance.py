"""Write-Tools: Wartung (Phase 6).

Rebuild (Thumbnails/Embeddings/Faces), Backup, FS↔DB-Abgleich (Reconcile) samt Report und
Reparatur-Aktionen, Wartungs-Kennzahlen. Registriert an `mcp_server` (Import in `server.py`
löst die `@mcp_server.tool()`-Decorator aus — siehe FINDINGS.md Phase 2).

`trigger_backup`/`list_backups`/`trigger_reconcile`/`trigger_rebuild` brauchen keine DB-Session
(reiner Job-Enqueue bzw. Dateisystem-Read) — direkter Aufruf statt über `run_endpoint()`
(FINDINGS.md → Phase 3/4/5/6: sync/session-lose Endpoints). `get_status`/`get_reconcile_report`/
`repair_reconcile` brauchen eine Session → `run_endpoint()`.

Gate (`confirm=true` nötig): `repair`, sobald eine Aktion `trash` oder `mark_missing` enthält —
reine `index`/`fix_path`-Aktionen laufen ohne Gate. `rebuild`/`backup`/`reconcile` sind
reversibel/regenerierend (kein Gate).
"""
from __future__ import annotations

from collections.abc import Awaitable

from fastapi import HTTPException

from photofant.api.maintenance import (
    BackupRequest,
    RebuildRequest,
    RepairActionDto,
    RepairRequest,
)
from photofant.api.maintenance import get_reconcile_report as _get_reconcile_report_endpoint
from photofant.api.maintenance import get_status as _get_status_endpoint
from photofant.api.maintenance import list_backups as _list_backups_endpoint
from photofant.api.maintenance import repair_reconcile as _repair_reconcile_endpoint
from photofant.api.maintenance import trigger_backup as _trigger_backup_endpoint
from photofant.api.maintenance import trigger_rebuild as _trigger_rebuild_endpoint
from photofant.api.maintenance import trigger_reconcile as _trigger_reconcile_endpoint
from photofant.jobs.rebuild_job import RebuildTarget
from photofant.mcp.adapter import run_endpoint
from photofant.mcp.gate import confirmation_required
from photofant.mcp.server import mcp_server

_GATED_REPAIR_ACTIONS = {"trash", "mark_missing"}


async def _run_or_error[Result](coro: Awaitable[Result]) -> Result | dict[str, object]:
    """Ruft eine Endpoint-Coroutine auf; mappt eine `HTTPException` (404/409/422 aus dem
    Endpoint) auf eine Text-Antwort für den Agenten, statt sie als Python-Exception
    hochzuwerfen (gleiches Muster wie `tools/organize.py`)."""
    try:
        return await coro
    except HTTPException as exc:
        return {"error": exc.detail, "status_code": exc.status_code}


@mcp_server.tool()
async def rebuild(target: RebuildTarget) -> dict[str, object]:
    """Regeneriert Thumbnails/Embeddings/Faces — asynchron, liefert eine `job_id`. Kein Gate
    (regeneriert nur, löscht keine Nutzdaten). **„Gesichter neu extrahieren" ist
    `target="faces"`.**"""
    result = await _run_or_error(_trigger_rebuild_endpoint(body=RebuildRequest(target=target)))
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


@mcp_server.tool()
async def backup(target_dir: str | None = None) -> dict[str, object]:
    """Löst ein DB-Backup aus — asynchron, liefert eine `job_id`. `target_dir` fehlt →
    Standard-Backup-Ordner."""
    result = await _run_or_error(_trigger_backup_endpoint(body=BackupRequest(target_dir=target_dir)))
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


@mcp_server.tool()
async def list_backups() -> dict[str, object]:
    """Listet vorhandene DB-Backups (Dateiname, Pfad, Größe in Bytes, Erstellzeit)."""
    result = await _run_or_error(_list_backups_endpoint())
    if isinstance(result, dict):
        return result
    return {"items": [item.model_dump(mode="json") for item in result]}


@mcp_server.tool()
async def maintenance_status() -> dict[str, object]:
    """Kennzahlen zur Wartung: DB-Größe, Thumbnail-/Foto-/Gesichts-Zahl, Cache-Größe,
    Festplattenbelegung des Datenordners."""
    result = await _run_or_error(run_endpoint(_get_status_endpoint))
    if isinstance(result, dict):
        return result
    return result.model_dump(mode="json")


@mcp_server.tool()
async def reconcile() -> dict[str, object]:
    """Stößt einen FS↔DB-Abgleich an (Waisen, fehlende Dateien, Pfad-Drift, verwaiste
    Gesichter, Fehlzuordnungen) — asynchron, liefert eine `job_id`. Ergebnis danach über
    `reconcile_report` lesen."""
    result = await _run_or_error(_trigger_reconcile_endpoint())
    if isinstance(result, dict):
        return result
    return {"job_id": result.job_id}


@mcp_server.tool()
async def reconcile_report() -> dict[str, object]:
    """Liest den letzten Abgleich-Report: Waisen-Dateien, fehlende Dateien, Pfad-Drift,
    verwaiste Gesichter, fehlzugeordnete Instanzen, bestätigt-fehlende Fotos, verwaiste
    Edits, verwaiste Face-Crops. Kein Report gelaufen → alle Listen leer. Vor `repair`
    aufrufen, um die `item`-Objekte für die Reparatur-Aktionen zu bekommen."""
    result = await _run_or_error(run_endpoint(_get_reconcile_report_endpoint))
    if isinstance(result, dict):
        return result
    return result.model_dump(mode="json")


@mcp_server.tool()
async def repair(actions: list[RepairActionDto], confirm: bool = False) -> dict[str, object]:
    """Führt Reparatur-Aktionen aus dem Abgleich-Report aus (`item` + `action` je Eintrag —
    Kandidaten liefert `reconcile_report`). **Gate**, sobald eine Aktion `trash` oder
    `mark_missing` ist (löscht eine Datei bzw. markiert ein Foto als fehlend) — reine
    `index`/`fix_path`-Aktionen laufen ohne Gate. Neu indizierte Dateien (`action="index"`)
    werden automatisch importiert (liefert dafür ggf. zusätzlich `import_job_id`)."""
    if any(entry.action in _GATED_REPAIR_ACTIONS for entry in actions):
        gated = [entry.action for entry in actions if entry.action in _GATED_REPAIR_ACTIONS]
        action_desc = f"Reparatur enthält {len(gated)} nicht-umkehrbare Aktion(en) ({', '.join(sorted(set(gated)))})"
        warning = confirmation_required(action_desc, confirm)
        if warning is not None:
            return {"warning": warning}
    result = await _run_or_error(run_endpoint(_repair_reconcile_endpoint, body=RepairRequest(actions=actions)))
    if isinstance(result, dict):
        return result
    return result.model_dump(mode="json")
