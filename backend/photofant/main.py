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
    auth,
    caption_presets,
    classification,
    classify,
    collections,
    comfyui,
    config,
    duplicates,
    edit_sessions,
    export,
    faces,
    health,
    info,
    jobs,
    knowledge,
    knowledge_ai,
    knowledge_tasks,
    maintenance,
    models,
    persons,
    prompt_templates,
    recommendations,
    review,
    review_queue,
    search,
    tags,
    trash,
)
from photofant.config import get_models_dir
from photofant.inference.generative_engine import generative_engine
from photofant.inference.gguf_engine import gguf_engine
from photofant.inference.session_manager import session_manager
from photofant.jobs.download_job import scan_models_dir
from photofant.jobs.face_folder_scan_job import enqueue_face_folder_scan
from photofant.jobs.queue import job_queue
from photofant.mcp.server import mcp_server, mount_mcp
from photofant.models.loader import load_manifest
from photofant.settings import ensure_settings_file, load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


async def _idle_eviction_loop() -> None:
    """Evict ONNX, generative (torch) and GGUF sessions that exceeded their idle timeout."""
    while True:
        await asyncio.sleep(60)
        session_manager.evict_idle()
        ai_idle_timeout = load_settings()["ai"]["idleTimeoutSeconds"]
        generative_engine.evict_idle(ai_idle_timeout)
        gguf_engine.evict_idle(ai_idle_timeout)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("Starting Photofant backend")
    ensure_settings_file()
    load_manifest()  # validate manifest.json at startup; logs errors, never crashes
    job_queue.start()
    # Auto-scan: register any models already present in models_dir so a new
    # instance picks up existing downloads without manual intervention.
    models_dir = get_models_dir()
    found = await asyncio.to_thread(scan_models_dir, models_dir)
    if found:
        log.info("Auto-scan: %d model(s) registered from %s", len(found), models_dir)
    else:
        log.debug("Auto-scan: no matching models found in %s", models_dir)

    # Warn loudly if the enabled embedder's vector width doesn't match the index
    # (a model swap that changed the dimension needs a migration + re-embed, ADR-022).
    from photofant.inference.image_embedder import warn_on_embedding_dim_mismatch
    warn_on_embedding_dim_mismatch()

    # Scan person face folders for manually placed images not yet in the DB.
    from photofant.config import get_data_root
    await enqueue_face_folder_scan(get_data_root())

    eviction_task = asyncio.create_task(_idle_eviction_loop())

    # Den Streamable-HTTP-Session-Manager der MCP-Sub-App im selben Lifespan
    # mitlaufen lassen — ein gemounteter Sub-App-Lifespan wird sonst nie gestartet
    # und der MCP-Teil würde beim ersten Request scheitern (ADR-019, Phase-1-Risiko).
    async with mcp_server.session_manager.run():
        yield

    log.info("Shutting down Photofant backend")
    eviction_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await eviction_task
    await job_queue.stop()
    generative_engine.unload()
    gguf_engine.unload()
    session_manager.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(title="Photofant", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    app.include_router(info.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(knowledge_ai.router, prefix="/api")
    app.include_router(knowledge_tasks.router, prefix="/api")
    app.include_router(recommendations.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(trash.router, prefix="/api")
    app.include_router(maintenance.router, prefix="/api")
    app.include_router(models.router, prefix="/api")
    app.include_router(caption_presets.router, prefix="/api")
    app.include_router(config.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(tags.router, prefix="/api")
    app.include_router(classify.router, prefix="/api")
    app.include_router(classification.router, prefix="/api")
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
    app.include_router(prompt_templates.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    mount_mcp(app)
    return app


app = create_app()
