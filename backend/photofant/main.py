from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from photofant.api import (
    assets,
    caption_presets,
    classify,
    collections,
    comfyui,
    config,
    duplicates,
    edit_sessions,
    faces,
    generative,
    health,
    info,
    jobs,
    maintenance,
    models,
    persons,
    review,
    review_queue,
    search,
    tags,
    trash,
)
from photofant.inference.generative_engine import generative_engine
from photofant.inference.session_manager import session_manager
from photofant.jobs.queue import job_queue
from photofant.models.loader import load_manifest
from photofant.settings import ensure_settings_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


async def _idle_eviction_loop() -> None:
    """Evict ONNX and generative sessions that have exceeded their idle timeout."""
    while True:
        await asyncio.sleep(60)
        session_manager.evict_idle()
        generative_engine.evict_idle()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("Starting Photofant backend")
    ensure_settings_file()
    load_manifest()  # validate manifest.json at startup; logs errors, never crashes
    job_queue.start()
    eviction_task = asyncio.create_task(_idle_eviction_loop())
    yield
    log.info("Shutting down Photofant backend")
    eviction_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await eviction_task
    await job_queue.stop()
    generative_engine.unload()
    session_manager.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(title="Photofant", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(info.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(trash.router, prefix="/api")
    app.include_router(maintenance.router, prefix="/api")
    app.include_router(models.router, prefix="/api")
    app.include_router(caption_presets.router, prefix="/api")
    app.include_router(config.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(tags.router, prefix="/api")
    app.include_router(classify.router, prefix="/api")
    app.include_router(collections.router, prefix="/api")
    app.include_router(review.router, prefix="/api")
    app.include_router(review_queue.router, prefix="/api")
    app.include_router(faces.router, prefix="/api")
    app.include_router(persons.router, prefix="/api")
    app.include_router(duplicates.router, prefix="/api")
    app.include_router(edit_sessions.router, prefix="/api")
    app.include_router(edit_sessions.versions_router, prefix="/api")
    app.include_router(comfyui.settings_router, prefix="/api")
    app.include_router(comfyui.comfyui_router, prefix="/api")
    app.include_router(generative.router, prefix="/api")
    return app


app = create_app()
