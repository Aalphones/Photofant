"""Capability-based image-embedder resolver + adapter registry (ADR-022).

Consumers ask for the embedder by *capability* (a role like "semantic_search"),
never by model name. Which concrete model answers is decided by the
ModelRegistry (whichever model with that role is enabled) — so a model swap
touches exactly three places: the adapter file, this registry, and the manifest,
plus a dimension migration only when the vector width changes. The step-by-step
swap runbook lives in docs/decisions/022-swappable-image-embedder.md.
"""
from __future__ import annotations

import logging

from photofant.inference.adapters.clip import CLIPEmbedder
from photofant.inference.adapters.siglip import SigLIPEmbedder
from photofant.inference.interfaces import Embedder

log = logging.getLogger(__name__)

# manifest_id -> adapter class. Adding a model = one line here + one manifest
# entry + the adapter file. Both models stay registered (CLIP is the rollback
# and the living proof the seam carries two adapters); exactly one is *enabled*
# in the ModelRegistry, because a coherent vector space needs a single model.
_IMAGE_EMBEDDER_ADAPTERS: dict[str, type[Embedder]] = {
    "clip-vit-l-14": CLIPEmbedder,
    "siglip2-large-patch16-384": SigLIPEmbedder,
}


def resolve_image_embedder(role: str = "semantic_search") -> Embedder | None:
    """Return the enabled image embedder for *role*, or None if none is active.

    Finds the enabled ModelRegistry row whose role matches, looks up the adapter
    class registered for that model's manifest_id, and instantiates it with the
    model's on-disk path. `role` stays a parameter (default "semantic_search")
    so a second, purely visual role (P37: "visual_rerank") plugs a DINOv2 adapter
    in without reopening this seam.
    """
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entries = (
            session.query(ModelRegistry)
            .filter_by(role=role, enabled=True)
            .order_by(ModelRegistry.id.desc())
            .all()
        )
        if len(entries) > 1:
            # Exclusivity invariant broken (should be impossible — deactivate_role_siblings
            # runs on every activate path — but a race between two concurrent activations
            # can still land both enabled=True). Silently picking SQLite's scan order here
            # crashed semantic search with a dim mismatch in the wild (2026-07-07): self-heal
            # instead of trusting query order, and log loud enough to notice next time.
            kept, *stale = entries
            log.error(
                "Exclusivity violated for role %r — %d models enabled (%s); keeping %r, disabling the rest",
                role, len(entries), [entry.manifest_id for entry in entries], kept.manifest_id,
            )
            for entry in stale:
                entry.enabled = False
            session.commit()
            entry = kept
        else:
            entry = entries[0] if entries else None
        if entry is None or not entry.path:
            log.info("No enabled image embedder for role %r — skipping", role)
            return None
        manifest_id = entry.manifest_id
        model_dir = entry.path

    adapter_class = _IMAGE_EMBEDDER_ADAPTERS.get(manifest_id)
    if adapter_class is None:
        log.warning(
            "Enabled model %r for role %r has no registered image-embedder adapter — skipping",
            manifest_id, role,
        )
        return None

    return adapter_class(model_dir=model_dir)


def warn_on_embedding_dim_mismatch() -> None:
    """Log a loud warning if the vector index width ≠ the active embedder's dim.

    A mismatch means the enabled model's vectors don't fit the vec0 table — a
    dimension migration plus a full re-embed is needed (ADR-022). We only warn,
    never crash: everything that doesn't touch embeddings keeps working, and the
    semantic search / dupe scan would otherwise fail with a confusing dim error.
    """
    from photofant.db import vector_index

    embedder = resolve_image_embedder()
    if embedder is None:
        return
    if embedder.dim != vector_index.EMBEDDING_DIM:
        log.warning(
            "Vektor-Index-Dimension %d passt nicht zur Modell-Dimension %d — "
            "Migration + Re-Embed nötig, sonst schlägt die semantische Suche fehl.",
            vector_index.EMBEDDING_DIM, embedder.dim,
        )
