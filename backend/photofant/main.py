from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from photofant.api import assets, caption_presets, classify, config, health, jobs, maintenance, models, search, trash
from photofant.inference.session_manager import session_manager
from photofant.jobs.queue import job_queue
from photofant.models.loader import load_manifest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("Starting Photofant backend")
    load_manifest()  # validate manifest.json at startup; logs errors, never crashes
    job_queue.start()
    yield
    log.info("Shutting down Photofant backend")
    await job_queue.stop()
    session_manager.evict_all()


def create_app() -> FastAPI:
    app = FastAPI(title="Photofant", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(trash.router, prefix="/api")
    app.include_router(maintenance.router, prefix="/api")
    app.include_router(models.router, prefix="/api")
    app.include_router(caption_presets.router, prefix="/api")
    app.include_router(config.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(classify.router, prefix="/api")
    return app


app = create_app()
