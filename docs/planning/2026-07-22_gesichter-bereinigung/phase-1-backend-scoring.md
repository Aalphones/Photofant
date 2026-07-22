# Phase 1 — Backend-Scoring-Modul + Settings

**Rating:** standard (Formel + Schwellen sind vollständig in [ADR-033](../../decisions/033-face-cleanup-score-on-demand.md) festgelegt, keine offene Design-Entscheidung).

## Kontext (lesen vor dem Bauen)

- [ADR-033](../../decisions/033-face-cleanup-score-on-demand.md) — Score-Formel, warum kein neues Schema.
- `backend/photofant/clustering/engine.py` — insbesondere `compute_person_centroid(session, person_id)`
  (Zeile ~284): liefert den L2-normierten Mittelwert-Embedding-Vektor aller Faces einer Person, `None`
  wenn keine Faces mit Embedding existieren. **Wiederverwenden, nicht duplizieren.**
- `backend/photofant/clustering/engine.py::_load_thresholds()` (Zeile ~28) — zeigt das Muster
  „Settings lazy im Funktionskörper laden, nicht am Modul-Top" (Import-Zyklen vermeiden). Gleiches
  Muster hier übernehmen.
- `backend/photofant/db/models.py` → `Face` (Suche nach `class Face`) — Spalten `embedding`
  (`deferred=True`, BLOB, ArcFace 512-d float32 L2-normiert), `score` (Detection-Confidence 0..1,
  kann `None` sein bei manuell importierten Faces), `resolution` (INTEGER, Crop-Pixel `height*width`,
  kann `None`/`0` sein), `is_upscaled` (BOOLEAN, Default `False`).
- `backend/photofant/settings.py` — drei Stellen, die bei jedem neuen Settings-Key alle drei
  angefasst werden müssen: `AppSettings`-TypedDict (Zeilen ~100-138), `SETTINGS_DEFAULTS`-Dict
  (Zeilen ~141-175 für die flachen `face_*`-Keys), `_EXPECTED_TYPES`-Dict (Zeilen ~257-289).

## Aufgabe

### 1. Settings erweitern (`backend/photofant/settings.py`)

Fünf neue Top-Level-Keys, eingefügt direkt nach der bestehenden Zeile `"face_min_cluster_size": 3,`
(bzw. der entsprechenden TypedDict-/Types-Zeile) — **an allen drei Stellen** ergänzen:

```python
face_cleanup_min_faces: int
face_cleanup_min_crop_side: int
face_cleanup_low_score_threshold: float
face_cleanup_identity_weight: float
face_cleanup_quality_weight: float
```

Defaults:

```python
"face_cleanup_min_faces": 3,
"face_cleanup_min_crop_side": 100,
"face_cleanup_low_score_threshold": 0.65,
"face_cleanup_identity_weight": 0.6,
"face_cleanup_quality_weight": 0.4,
```

`_EXPECTED_TYPES`-Einträge:

```python
"face_cleanup_min_faces": int,
"face_cleanup_min_crop_side": int,
"face_cleanup_low_score_threshold": (float, int),
"face_cleanup_identity_weight": (float, int),
"face_cleanup_quality_weight": (float, int),
```

Kurzer Kommentar direkt über den Defaults im Stil der bestehenden `dupe_dino_threshold`-Kommentare:

```python
# Gesichts-Bereinigung (ADR-033) — Tuning-Konstanten ohne eigene Einstellungen-UI (bewusster
# Scope-Cut, siehe ADR). identity_weight + quality_weight sollten zu 1.0 summieren, damit
# cleanup_score in [0, 1] bleibt; keine Laufzeit-Validierung dafür (Vertrauensvorschuss wie
# bei recommendations.weights).
```

### 2. Neues Modul `backend/photofant/clustering/cleanup.py`

Exakter Inhalt (Sonnet-tauglich vollständig ausformuliert, keine Lücken):

```python
"""Face-Bereinigung — Score pro Face, wie sehr es zur zugewiesenen Person passt.

Kombiniert zwei unabhängige Signale (ADR-033):
  - Identität: Cosine-Distanz zum Personen-Embedding-Centroid (compute_person_centroid).
  - Qualität: schlechte Crop-Auflösung, niedriger Detection-Score, is_upscaled-Flag —
    das schlechteste der drei Signale zählt, keine Mittelung.

Stateless: keine Persistenz, jeder Aufruf rechnet frisch (Begründung: ADR-033).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.clustering.engine import compute_person_centroid
from photofant.db.models import Face

REASON_IDENTITY_MISMATCH = "identity_mismatch"
REASON_LOW_RESOLUTION = "low_resolution"
REASON_LOW_DETECTION_SCORE = "low_detection_score"
REASON_UPSCALED = "upscaled"


@dataclass
class FaceCleanupScore:
    face_id: int
    identity_distance: float | None
    cleanup_score: float
    reasons: list[str] = field(default_factory=list)


def _load_cleanup_settings() -> dict[str, float]:
    from photofant.settings import load_settings

    settings = load_settings()
    return {
        "min_faces": float(settings.get("face_cleanup_min_faces", 3)),
        "min_crop_side": float(settings.get("face_cleanup_min_crop_side", 100)),
        "low_score_threshold": float(settings.get("face_cleanup_low_score_threshold", 0.65)),
        "identity_weight": float(settings.get("face_cleanup_identity_weight", 0.6)),
        "quality_weight": float(settings.get("face_cleanup_quality_weight", 0.4)),
        "review_threshold": float(settings.get("face_review_threshold", 0.45)),
    }


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def compute_person_cleanup_scores(session: Session, person_id: int) -> list[FaceCleanupScore]:
    """Score every face of a person by how likely it is a cleanup candidate.

    Returns one entry per face belonging to person_id, in no particular order —
    callers sort by cleanup_score themselves. Empty list if the person has no faces.
    """
    cfg = _load_cleanup_settings()

    rows = session.execute(
        select(Face.id, Face.embedding, Face.score, Face.resolution, Face.is_upscaled)
        .where(Face.person_id == person_id)
    ).all()

    if not rows:
        return []

    centroid: np.ndarray | None = None
    if len(rows) >= cfg["min_faces"]:
        centroid = compute_person_centroid(session, person_id)

    identity_norm = max(1.0 - cfg["review_threshold"], 1e-6)
    results: list[FaceCleanupScore] = []

    for face_id, embedding_bytes, score, resolution, is_upscaled in rows:
        reasons: list[str] = []
        identity_distance: float | None = None
        identity_penalty = 0.0

        if centroid is not None and embedding_bytes is not None:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            similarity = float(np.dot(embedding, centroid))
            identity_distance = 1.0 - similarity
            identity_penalty = _clamp01(identity_distance / identity_norm)
            if identity_penalty >= 0.5:
                reasons.append(REASON_IDENTITY_MISMATCH)

        res_penalty = 0.0
        if resolution is not None and resolution > 0:
            crop_side = resolution ** 0.5
            if crop_side < cfg["min_crop_side"]:
                reasons.append(REASON_LOW_RESOLUTION)
                res_penalty = _clamp01((cfg["min_crop_side"] - crop_side) / cfg["min_crop_side"])

        score_penalty = 0.0
        if score is not None and score < cfg["low_score_threshold"]:
            reasons.append(REASON_LOW_DETECTION_SCORE)
            score_penalty = _clamp01(
                (cfg["low_score_threshold"] - score) / cfg["low_score_threshold"]
            )

        upscale_penalty = 0.0
        if is_upscaled:
            reasons.append(REASON_UPSCALED)
            upscale_penalty = 1.0

        quality_penalty = max(res_penalty, score_penalty, upscale_penalty)
        cleanup_score = _clamp01(
            cfg["identity_weight"] * identity_penalty + cfg["quality_weight"] * quality_penalty
        )

        results.append(FaceCleanupScore(
            face_id=int(face_id),
            identity_distance=identity_distance,
            cleanup_score=cleanup_score,
            reasons=reasons,
        ))

    return results
```

Hinweise für den Umsetzer:
- `Face.embedding` ist `deferred=True` am ORM-Mapping — der explizite `select(Face.id, Face.embedding, ...)`
  oben umgeht das (liefert rohe Tupel, keine ORM-Instanzen), **kein** `.options(undefer(...))` nötig.
- `resolution ** 0.5` auf einem SQL-`int`-Wert liefert einen Python `float` — kein Cast nötig.
- Faces ganz ohne Embedding (`embedding_bytes is None`, z.B. während der Verarbeitung) bekommen
  `identity_distance=None`, `identity_penalty=0.0` — sie werden nur über Qualitätssignale bewertet,
  nie fälschlich als Identitäts-Ausreißer geflaggt.

## Akzeptanzkriterien

- `compute_person_cleanup_scores` importierbar aus `photofant.clustering.cleanup`, wirft nicht bei
  einer Person ohne Faces (leere Liste) und nicht bei einer Person mit Faces ohne Embedding.
- Die fünf neuen Settings sind an allen drei Stellen in `settings.py` vorhanden; `python -c "from photofant.settings import load_settings; print(load_settings()['face_cleanup_min_faces'])"` liefert `3` auf einer frischen Instanz.
- Kein bestehender Import bricht (`ruff`/`mypy` bzw. das Projekt-Äquivalent sauber, falls konfiguriert).

## Checkliste

- [x] `backend/photofant/settings.py`: 5 Keys in `AppSettings`, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`
- [x] `backend/photofant/clustering/cleanup.py` neu angelegt (Inhalt wie oben)
- [x] Kurzer manueller Check: Settings laden funktioniert, Modul importierbar

## Report-Back

- `load_settings()['face_cleanup_min_faces']` liefert `3` auf frischer Instanz — verifiziert.
- `ruff check` + `mypy` auf beiden geänderten Dateien: sauber.
- Plan 1:1 umgesetzt, keine Abweichungen, keine Findings für spätere Phasen.
