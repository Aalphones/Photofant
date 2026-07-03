"""Face-Clustering engine — initial HDBSCAN + incremental cosine matching.

Initial clustering: HDBSCAN over all face embeddings creates person candidates.
Incremental matching: a single new face is matched against existing persons via
cosine similarity with score-band logic (auto / review / unknown).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import Face, Person

log = logging.getLogger(__name__)


@dataclass
class MatchResult:
    person_id: int | None
    score: float
    band: str  # "auto" | "review" | "unknown"


def _load_thresholds() -> tuple[float, float, int]:
    from photofant.settings import load_settings

    settings = load_settings()
    auto_threshold: float = float(settings.get("face_auto_threshold", 0.6))
    review_threshold: float = float(settings.get("face_review_threshold", 0.45))
    min_cluster_size: int = int(settings.get("face_min_cluster_size", 2))
    return auto_threshold, review_threshold, min_cluster_size


def match_face_incremental(session: Session, face_id: int) -> MatchResult:
    """Match a single face against existing persons via cosine similarity.

    Score bands (configurable in settings):
      - auto  (≥ auto_threshold):  assign to best-matching person
      - review (review..auto):     suggestion for review queue
      - unknown (below review):    stays in _unknown
    """
    from photofant.db.face_vector_index import search_disjoint_persons

    face = session.get(Face, face_id)
    if face is None or face.embedding is None:
        return MatchResult(person_id=None, score=0.0, band="unknown")

    embedding = np.frombuffer(face.embedding, dtype=np.float32).copy()
    auto_threshold, review_threshold, _ = _load_thresholds()

    unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
    unknown_person_id = unknown_person.id if unknown_person else None

    matches = search_disjoint_persons(
        session, embedding, exclude_face_id=face_id, limit=1,
    )

    if not matches:
        return MatchResult(person_id=unknown_person_id, score=0.0, band="unknown")

    best = matches[0]
    best_score = float(best["score"])
    best_person_id = int(best["person_id"])

    if best_person_id == unknown_person_id:
        return MatchResult(person_id=unknown_person_id, score=best_score, band="unknown")

    if best_score >= auto_threshold:
        return MatchResult(person_id=best_person_id, score=best_score, band="auto")

    if best_score >= review_threshold:
        return MatchResult(person_id=best_person_id, score=best_score, band="review")

    return MatchResult(person_id=unknown_person_id, score=best_score, band="unknown")


def _run_hdbscan(embeddings: np.ndarray, min_cluster_size: int, epsilon: float) -> np.ndarray:
    from sklearn.cluster import HDBSCAN as SklearnHDBSCAN

    clusterer = SklearnHDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        cluster_selection_epsilon=epsilon,
        metric="cosine",
        store_centers="centroid",
    )
    return clusterer.fit_predict(embeddings)


def run_initial_clustering(session: Session) -> dict[str, int]:
    """Match unassigned faces against existing persons first, then HDBSCAN the rest.

    Returns stats: {persons_created, faces_assigned, noise_count, matched_auto,
    matched_review}. Faces with ``fixed_person`` instances are excluded from
    both the matching pre-stage and HDBSCAN redistribution.
    """
    from datetime import UTC, datetime

    from photofant.db.models import AssetInstance, ReviewItem

    auto_threshold, review_threshold, min_cluster_size = _load_thresholds()

    rows = session.execute(
        select(Face.id, Face.embedding).where(Face.embedding.isnot(None))
    ).fetchall()

    if not rows:
        log.info("No face embeddings found — nothing to cluster")
        return {
            "persons_created": 0, "faces_assigned": 0, "noise_count": 0,
            "matched_auto": 0, "matched_review": 0,
        }

    face_ids = [int(row[0]) for row in rows]
    embeddings = np.array(
        [np.frombuffer(row[1], dtype=np.float32) for row in rows],
        dtype=np.float32,
    )

    unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
    unknown_person_id = unknown_person.id if unknown_person else 1

    fixed_face_ids: set[int] = set()
    fixed_rows = session.execute(
        select(AssetInstance.asset_id)
        .where(AssetInstance.fixed_person.is_(True))
    ).fetchall()
    fixed_asset_ids = {int(row[0]) for row in fixed_rows}

    if fixed_asset_ids:
        fixed_faces = session.execute(
            select(Face.id).where(Face.asset_id.in_(fixed_asset_ids))
        ).fetchall()
        fixed_face_ids = {int(row[0]) for row in fixed_faces}

    # Matching pre-stage: before HDBSCAN forms new person buckets, check whether an
    # existing person now covers each still-unknown face (e.g. the person was
    # created after the previous clustering run). Reuses the same score bands as
    # the incremental match that runs right after import.
    matched_auto = 0
    matched_review = 0

    for face_id in face_ids:
        if face_id in fixed_face_ids:
            continue
        face = session.get(Face, face_id)
        if face is None or face.person_id != unknown_person_id:
            continue

        result = match_face_incremental(session, face_id)

        if result.band == "auto" and result.person_id is not None:
            face.person_id = result.person_id
            matched_auto += 1
            log.info(
                "Face %d pre-matched (auto) to person %d (score=%.3f)",
                face_id, result.person_id, result.score,
            )

        elif result.band == "review" and result.person_id is not None:
            existing = session.query(ReviewItem).filter(
                ReviewItem.type == "face_suggestion",
                ReviewItem.face_id == face_id,
                ReviewItem.resolved_at.is_(None),
            ).first()
            if existing is None:
                asset_id = face.asset_id or 0
                session.add(ReviewItem(
                    type="face_suggestion",
                    asset_a_id=asset_id,
                    asset_b_id=asset_id,
                    phash_distance=0,
                    face_id=face_id,
                    suggested_person_id=result.person_id,
                    score=result.score,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                ))
            matched_review += 1

    session.flush()

    log.info(
        "Clustering %d face embeddings (min_cluster_size=%d, epsilon=%.2f)",
        len(face_ids), min_cluster_size, 1.0 - auto_threshold,
    )

    try:
        labels = _run_hdbscan(embeddings, min_cluster_size, 1.0 - auto_threshold)
    except TypeError as error:
        # Known scikit-learn bug: epsilon-based cluster selection
        # (traverse_upwards in _tree.pyx) coerces a multi-row numpy result into a
        # scalar and crashes when the condensed tree has tied merge distances —
        # which real face-embedding sets large enough to have near-duplicate
        # faces run into. Falling back to epsilon=0 (pure excess-of-mass
        # selection) avoids that code path entirely.
        if "0-dimensional arrays" not in str(error):
            raise
        log.warning(
            "HDBSCAN epsilon-based cluster selection hit a tied-distance bug (%s) — "
            "retrying without epsilon merge", error,
        )
        labels = _run_hdbscan(embeddings, min_cluster_size, 0.0)
    except ImportError:
        log.warning("scikit-learn HDBSCAN not available — falling back to DBSCAN")
        from sklearn.cluster import DBSCAN

        clusterer = DBSCAN(eps=1 - auto_threshold, min_samples=min_cluster_size, metric="cosine")
        labels = clusterer.fit_predict(embeddings)

    unique_labels = set(labels)
    unique_labels.discard(-1)

    persons_created = 0
    faces_assigned = 0
    noise_count = 0

    for label in sorted(unique_labels):
        cluster_indices = [index for index, cluster_label in enumerate(labels) if cluster_label == label]
        cluster_face_ids = [face_ids[index] for index in cluster_indices]

        assignable_face_ids = [fid for fid in cluster_face_ids if fid not in fixed_face_ids]
        if not assignable_face_ids:
            continue

        # Collect faces that are actually still in _unknown before creating a Person row.
        # Without this check, re-running clustering creates empty nameless Person rows
        # for clusters whose faces were already assigned in a previous run.
        faces_from_unknown: list[Face] = []
        for fid in assignable_face_ids:
            session.execute(select(Face).where(Face.id == fid).with_for_update())
            face = session.get(Face, fid)
            if face is not None and face.person_id == unknown_person_id:
                faces_from_unknown.append(face)

        if not faces_from_unknown:
            continue

        person = Person(name=None, is_unknown=False)
        session.add(person)
        session.flush()
        persons_created += 1

        for face in faces_from_unknown:
            face.person_id = person.id
            faces_assigned += 1

    noise_indices = [index for index, cluster_label in enumerate(labels) if cluster_label == -1]
    noise_count = len(noise_indices)

    session.commit()
    log.info(
        "Clustering done: %d persons created, %d faces assigned, %d noise, "
        "%d matched (auto), %d matched (review)",
        persons_created, faces_assigned, noise_count, matched_auto, matched_review,
    )
    return {
        "persons_created": persons_created,
        "faces_assigned": faces_assigned,
        "noise_count": noise_count,
        "matched_auto": matched_auto,
        "matched_review": matched_review,
    }


def compute_person_centroid(session: Session, person_id: int) -> np.ndarray | None:
    """Compute the mean embedding (centroid) for all faces of a person."""
    rows = session.execute(
        select(Face.embedding)
        .where(Face.person_id == person_id, Face.embedding.isnot(None))
    ).fetchall()

    if not rows:
        return None

    embeddings = np.array(
        [np.frombuffer(row[0], dtype=np.float32) for row in rows],
        dtype=np.float32,
    )
    centroid = embeddings.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid /= norm
    return centroid
