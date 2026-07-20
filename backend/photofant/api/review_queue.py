"""Review-Queue API — face-suggestion review (confirm / reject / reassign)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import Face, Person, ReviewItem
from photofant.db.session import get_session

if TYPE_CHECKING:
    from photofant.knowledge.service import KnowledgeService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/review-queue")

DbSession = Annotated[Session, Depends(get_session)]


class FaceReviewItemDto(BaseModel):
    id: int
    face_id: int
    suggested_person_id: int | None
    suggested_person_name: str | None
    score: float
    asset_id: int
    crop_url: str


class ReviewActionRequest(BaseModel):
    action: Literal["confirm", "reject", "reassign"]
    person_id: int | None = None


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _needs_knowledge_lookup(
    knowledge_service: KnowledgeService, auto_lookup_enabled: bool, person: Person | None
) -> bool:
    """P24: soll für `person` ein `KnowledgeLookupJob` angestoßen werden?

    Reine Entscheidungsfunktion (kein I/O außer dem Cache-Read über den Service) — dadurch
    ohne HTTP-Layer testbar. `False` bei fehlendem Namen: eine unbenannte Person liefert
    keinen sinnvollen `ref` für den Lookup, und der spätere Wizard (Phase 2) braucht den
    Namen ohnehin als Titel-Vorbelegung.
    """
    if not auto_lookup_enabled or person is None or not person.name:
        return False
    return knowledge_service.linked_entity_ref("person", person.id) is None


@router.get("", response_model=list[FaceReviewItemDto])
async def list_review_queue(session: DbSession) -> list[FaceReviewItemDto]:
    """Return all pending face-suggestion review items."""
    items = (
        session.query(ReviewItem)
        .filter(
            ReviewItem.type == "face_suggestion",
            ReviewItem.resolved_at.is_(None),
        )
        .order_by(ReviewItem.score.desc(), ReviewItem.id)
        .all()
    )

    results: list[FaceReviewItemDto] = []
    for item in items:
        if item.face_id is None:
            continue
        face = session.get(Face, item.face_id)
        if face is None:
            continue

        person_name: str | None = None
        if item.suggested_person_id is not None:
            person = session.get(Person, item.suggested_person_id)
            if person is not None:
                person_name = person.name

        results.append(FaceReviewItemDto(
            id=item.id,
            face_id=item.face_id,
            suggested_person_id=item.suggested_person_id,
            suggested_person_name=person_name,
            score=item.score or 0.0,
            asset_id=face.asset_id or 0,
            crop_url=f"/api/faces/{item.face_id}/thumbnail",
        ))

    return results


@router.post("/{face_id}")
async def resolve_face_review(
    face_id: int,
    body: ReviewActionRequest,
    session: DbSession,
) -> dict[str, str]:
    """Confirm, reject, or reassign a face review suggestion."""
    item = (
        session.query(ReviewItem)
        .filter(
            ReviewItem.type == "face_suggestion",
            ReviewItem.face_id == face_id,
            ReviewItem.resolved_at.is_(None),
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="No pending review item for this face")

    face = session.get(Face, face_id)
    if face is None:
        raise HTTPException(status_code=404, detail="Face not found")

    action = body.action

    if action == "confirm":
        target_person_id = item.suggested_person_id
        if target_person_id is None:
            raise HTTPException(status_code=400, detail="No suggested person to confirm")

        from photofant.config import get_data_root
        from photofant.media.person_folders import materialize_assignment, move_face_crops_to_person

        face.person_id = target_person_id
        session.flush()

        data_root = get_data_root()
        materialize_assignment(session, face.asset_id, target_person_id, data_root)
        move_face_crops_to_person(session, face.asset_id, target_person_id, data_root)

        item.resolved_at = _now_utc()
        item.resolution = "confirmed"

        if face.asset_id is not None:
            from photofant.jobs.recommendation_job import invalidate_recommendations

            invalidate_recommendations(session, [face.asset_id])

        session.commit()

        from photofant.jobs.collections_job import enqueue_reevaluate_assets

        if face.asset_id is not None:
            import asyncio
            asyncio.ensure_future(enqueue_reevaluate_assets([face.asset_id]))

        # P24: Person bestätigt ohne verknüpfte Entity → Wissens-Lookup anstoßen (additiv,
        # ändert den Move-Pfad oben nicht — siehe README-Chesterton). Sackgassen-Job, kein
        # Rekursionsschutz nötig (ADR-014).
        from photofant.knowledge.service import KnowledgeService
        from photofant.knowledge.vault import open_vault
        from photofant.settings import load_settings

        target_person = session.get(Person, target_person_id)
        auto_lookup_enabled = load_settings()["knowledge"]["auto_lookup"]
        knowledge_service = KnowledgeService(session, open_vault())
        if _needs_knowledge_lookup(knowledge_service, auto_lookup_enabled, target_person):
            import asyncio

            from photofant.jobs.knowledge_lookup_job import enqueue_knowledge_lookup
            from photofant.knowledge.tasks import TaskKind

            assert target_person is not None  # für mypy — von _needs_knowledge_lookup geprüft
            asyncio.ensure_future(
                enqueue_knowledge_lookup(
                    TaskKind.NEW_PERSON, target_person.name, {"person_id": target_person_id}
                )
            )

        log.info("Face %d confirmed → person %d", face_id, target_person_id)
        return {"status": "confirmed"}

    elif action == "reject":
        unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
        if unknown_person is not None and face.person_id != unknown_person.id:
            from photofant.config import get_data_root
            from photofant.media.person_folders import reassign_face

            data_root = get_data_root()
            reassign_face(session, face_id, unknown_person.id, data_root)

        item.resolved_at = _now_utc()
        item.resolution = "rejected"

        if face.asset_id is not None:
            from photofant.jobs.recommendation_job import invalidate_recommendations

            invalidate_recommendations(session, [face.asset_id])

        session.commit()

        log.info("Face %d rejected → _unknown", face_id)
        return {"status": "rejected"}

    elif action == "reassign":
        target_person_id = body.person_id
        if target_person_id is None:
            raise HTTPException(status_code=422, detail="person_id required for reassign")

        target_person = session.get(Person, target_person_id)
        if target_person is None:
            raise HTTPException(status_code=404, detail="Target person not found")

        from photofant.config import get_data_root
        from photofant.media.person_folders import reassign_face

        data_root = get_data_root()
        reassign_face(session, face_id, target_person_id, data_root)

        item.resolved_at = _now_utc()
        item.resolution = f"reassigned:{target_person_id}"

        if face.asset_id is not None:
            from photofant.jobs.recommendation_job import invalidate_recommendations

            invalidate_recommendations(session, [face.asset_id])

        session.commit()

        if face.asset_id is not None:
            import asyncio

            from photofant.jobs.collections_job import enqueue_reevaluate_assets
            asyncio.ensure_future(enqueue_reevaluate_assets([face.asset_id]))

        log.info("Face %d reassigned → person %d", face_id, target_person_id)
        return {"status": "reassigned"}

    raise HTTPException(status_code=422, detail=f"Unknown action: {action}")
