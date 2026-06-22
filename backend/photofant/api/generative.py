"""API endpoints for the generative backend (ADR-002)."""
from __future__ import annotations

from fastapi import APIRouter

from photofant.inference.generative_engine import (
    GenerativeAvailability,
    check_generative_available,
    generative_engine,
)
from photofant.jobs.install_generative_job import enqueue_install_generative

router = APIRouter(tags=["generative"])


@router.get("/generative/status")
async def generative_status() -> dict:
    """Return whether the generative backend is available and what model is loaded."""
    availability = check_generative_available()
    return {
        "available": availability is GenerativeAvailability.AVAILABLE,
        "status": str(availability),
        "loaded_model": generative_engine.loaded_model_id,
    }


@router.post("/generative/install")
async def install_generative() -> dict:
    """Trigger installation of the generative dependency group."""
    availability = check_generative_available()
    if availability is GenerativeAvailability.AVAILABLE:
        return {"message": "Generative Abhängigkeiten sind bereits installiert.", "already_installed": True}

    job_status = await enqueue_install_generative()
    return {
        "message": "Installation gestartet — Fortschritt über /api/jobs abrufbar.",
        "job_id": job_status.id,
        "already_installed": False,
    }


@router.post("/generative/unload")
async def unload_generative() -> dict:
    """Unload the currently loaded generative pipeline to free VRAM."""
    loaded = generative_engine.loaded_model_id
    if loaded is None:
        return {"message": "Kein generatives Modell geladen."}
    generative_engine.unload()
    return {"message": f"Modell '{loaded}' entladen, VRAM freigegeben."}
