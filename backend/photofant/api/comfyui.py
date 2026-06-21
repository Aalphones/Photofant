"""
GET  /api/settings/comfyui        — read ComfyUI settings block
PUT  /api/settings/comfyui        — replace ComfyUI settings block
POST /api/comfyui/test-connection  — probe ComfyUI /system_stats
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from photofant.comfyui.client import ComfyUIClient, ComfyUIError
from photofant.settings import load_settings, save_settings

log = logging.getLogger(__name__)

settings_router = APIRouter(prefix="/settings/comfyui")
comfyui_router = APIRouter(prefix="/comfyui")


# ── Schemas ──────────────────────────────────────────────────────────────────

class ComfyUISettingsResponse(BaseModel):
    enabled: bool
    base_url: str
    client_id: str
    output_dir: str
    timeout: int


class ComfyUISettingsPutRequest(BaseModel):
    enabled: bool
    base_url: str
    client_id: str
    output_dir: str
    timeout: int


class TestConnectionResponse(BaseModel):
    ok: bool
    detail: str


# ── Settings routes ───────────────────────────────────────────────────────────

@settings_router.get("", response_model=ComfyUISettingsResponse)
def get_comfyui_settings() -> ComfyUISettingsResponse:
    cfg = load_settings()
    comfyui = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    return ComfyUISettingsResponse(
        enabled=bool(comfyui.get("enabled", False)),
        base_url=str(comfyui.get("base_url", "http://127.0.0.1:8188")),
        client_id=str(comfyui.get("client_id", "photofant")),
        output_dir=str(comfyui.get("output_dir", "")),
        timeout=int(comfyui.get("timeout", 10)),
    )


@settings_router.put("", response_model=ComfyUISettingsResponse)
def put_comfyui_settings(body: ComfyUISettingsPutRequest) -> ComfyUISettingsResponse:
    if body.timeout < 1 or body.timeout > 300:
        raise HTTPException(status_code=422, detail="timeout muss zwischen 1 und 300 Sekunden liegen")
    cfg = load_settings()
    cfg["comfyui"] = {  # type: ignore[typeddict-item]
        "enabled": body.enabled,
        "base_url": body.base_url.strip(),
        "client_id": body.client_id.strip() or "photofant",
        "output_dir": body.output_dir.strip(),
        "timeout": body.timeout,
    }
    save_settings(cfg)
    log.info("comfyui settings updated: enabled=%s url=%s", body.enabled, body.base_url)
    return ComfyUISettingsResponse(**cfg["comfyui"])  # type: ignore[typeddict-item]


# ── Test-connection route ─────────────────────────────────────────────────────

@comfyui_router.post("/test-connection", response_model=TestConnectionResponse)
def test_connection() -> TestConnectionResponse:
    cfg = load_settings()
    comfyui = cfg.get("comfyui", {})  # type: ignore[attr-defined]
    base_url = str(comfyui.get("base_url", "http://127.0.0.1:8188"))
    timeout = float(comfyui.get("timeout", 10))

    client = ComfyUIClient(base_url=base_url, timeout=timeout)
    try:
        stats = client.system_stats()
        version = str(stats.get("system", {}).get("comfyui_version", "unbekannt"))  # type: ignore[union-attr]
        return TestConnectionResponse(ok=True, detail=f"ComfyUI {version} erreichbar")
    except ComfyUIError as exc:
        detail = f"{exc.what_expected} — {exc.what_found}. {exc.next_step}."
        return TestConnectionResponse(ok=False, detail=detail)
