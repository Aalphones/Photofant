"""InsightFace buffalo_l adapter — implements FaceEngine via raw ONNX Runtime.

buffalo_l is an InsightFace model bundle.  Expected directory layout:
  <model_dir>/
      det_10g.onnx      — SCRFD face detector
      w600k_r50.onnx    — ArcFace recognizer (512-d embedding)
      genderage.onnx    — age / gender estimator

All three models run on the shared session_manager (lazy load, idle eviction).

Detection pipeline per image:
  1. Resize + pad → 640×640 blob → SCRFD → raw anchor predictions
  2. Decode anchors, NMS → BBoxes + 5-point landmarks per face
  3. Affine-align each face to canonical 112×112 landmarks → ArcFace → 512-d embedding
  4. Same alignment resized to 96×96 → genderage → age
  5. Return list[dict] with keys: bbox, landmarks, embedding, score, age

Crop (what gets saved to disk) uses the original BBox + padding, NOT the
aligned version — alignment is only used internally for embedding computation.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

_MANIFEST_ID = "buffalo_l"

# Canonical 5-point landmarks for 112×112 ArcFace alignment (InsightFace standard)
_ARCFACE_DST = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041],
], dtype=np.float32)

# SCRFD anchor config for det_10g (strides 8 / 16 / 32, 2 anchors per cell)
_SCRFD_STRIDES = (8, 16, 32)
_SCRFD_NUM_ANCHORS = 2

_DET_INPUT_SIZE = 640
_IOU_THRESHOLD = 0.45
_CONF_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Preprocessing helpers
# ---------------------------------------------------------------------------

def _make_scrfd_blob(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Resize + pad to 640×640, normalize for SCRFD.  Returns (blob, scale)."""
    from PIL import Image as PILImage

    height, width = image.shape[:2]
    scale = _DET_INPUT_SIZE / max(height, width)
    new_w = int(round(width * scale))
    new_h = int(round(height * scale))

    resized = np.array(PILImage.fromarray(image).resize((new_w, new_h), PILImage.BILINEAR))
    padded = np.zeros((_DET_INPUT_SIZE, _DET_INPUT_SIZE, 3), dtype=np.uint8)
    padded[:new_h, :new_w] = resized

    blob = (padded.astype(np.float32) - 127.5) / 128.0
    blob = np.transpose(blob, (2, 0, 1))[np.newaxis, :]
    return blob, scale


def _generate_anchors(height: int, width: int, stride: int) -> np.ndarray:
    """Generate anchor center points for one SCRFD feature-map level."""
    grid_h, grid_w = height // stride, width // stride
    cy, cx = np.mgrid[0:grid_h, 0:grid_w]
    centers = np.stack([cx, cy], axis=-1).astype(np.float32).reshape(-1, 2)
    centers = (centers + 0.5) * stride
    # Each cell has _SCRFD_NUM_ANCHORS anchors stacked
    return np.repeat(centers, _SCRFD_NUM_ANCHORS, axis=0)


def _decode_scrfd_outputs(
    outputs: dict[str, np.ndarray],
    input_height: int,
    input_width: int,
    scale: float,
) -> list[dict]:
    """Decode multi-scale SCRFD outputs into BBox + landmark dicts.

    SCRFD outputs are grouped by stride; we sort them by shape to match
    strides 8→16→32 (largest feature map first) regardless of output name order.
    """
    # Separate score, bbox, kps tensors — identify by last-dim shape
    score_tensors: list[np.ndarray] = []
    bbox_tensors: list[np.ndarray] = []
    kps_tensors: list[np.ndarray] = []

    for tensor in outputs.values():
        if tensor.ndim > 1 and tensor.shape[0] == 1:
            tensor = tensor.squeeze(0)  # remove batch dim if present
        last_dim = tensor.shape[-1]
        if last_dim == 1:
            score_tensors.append(tensor.reshape(-1))
        elif last_dim == 4:
            bbox_tensors.append(tensor.reshape(-1, 4))
        elif last_dim == 10:
            kps_tensors.append(tensor.reshape(-1, 5, 2))

    # Sort by descending number of rows (stride 8 = largest map = most anchors)
    score_tensors.sort(key=lambda t: -t.shape[0])
    bbox_tensors.sort(key=lambda t: -t.shape[0])
    kps_tensors.sort(key=lambda t: -t.shape[0])

    all_scores: list[float] = []
    all_bboxes: list[np.ndarray] = []
    all_landmarks: list[np.ndarray] = []

    for stride_idx, stride in enumerate(_SCRFD_STRIDES):
        if stride_idx >= len(score_tensors):
            break

        scores = score_tensors[stride_idx]
        boxes_raw = bbox_tensors[stride_idx]
        anchors = _generate_anchors(input_height, input_width, stride)

        if len(anchors) != len(scores):
            log.warning(
                "SCRFD stride %d: anchor count %d ≠ score count %d — skipping",
                stride, len(anchors), len(scores),
            )
            continue

        mask = scores >= _CONF_THRESHOLD
        if not np.any(mask):
            continue

        selected_scores = scores[mask]
        selected_anchors = anchors[mask]
        selected_boxes = boxes_raw[mask]

        # Decode LTRB relative offsets (in feature-map stride units)
        x1 = (selected_anchors[:, 0] - selected_boxes[:, 0] * stride) / scale
        y1 = (selected_anchors[:, 1] - selected_boxes[:, 1] * stride) / scale
        x2 = (selected_anchors[:, 0] + selected_boxes[:, 2] * stride) / scale
        y2 = (selected_anchors[:, 1] + selected_boxes[:, 3] * stride) / scale
        decoded_bboxes = np.stack([x1, y1, x2, y2], axis=-1)

        all_scores.extend(selected_scores.tolist())
        all_bboxes.append(decoded_bboxes)

        if stride_idx < len(kps_tensors):
            kps_raw = kps_tensors[stride_idx][mask]
            # Each of 5 points: anchor + offset * stride
            kps_decoded = np.zeros_like(kps_raw)
            kps_decoded[:, :, 0] = (
                selected_anchors[:, 0:1] + kps_raw[:, :, 0] * stride
            ) / scale
            kps_decoded[:, :, 1] = (
                selected_anchors[:, 1:2] + kps_raw[:, :, 1] * stride
            ) / scale
            all_landmarks.append(kps_decoded)

    if not all_bboxes:
        return []

    bboxes = np.concatenate(all_bboxes, axis=0)
    scores_arr = np.array(all_scores, dtype=np.float32)
    landmarks_arr = np.concatenate(all_landmarks, axis=0) if all_landmarks else None

    # NMS
    keep = _nms(bboxes, scores_arr, _IOU_THRESHOLD)

    results: list[dict] = []
    for index in keep:
        entry: dict = {
            "bbox": bboxes[index].tolist(),
            "score": float(scores_arr[index]),
            "landmarks": landmarks_arr[index].tolist() if landmarks_arr is not None else None,
        }
        results.append(entry)

    return results


def _nms(bboxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    """Simple greedy NMS — returns indices of kept boxes."""
    x1, y1, x2, y2 = bboxes[:, 0], bboxes[:, 1], bboxes[:, 2], bboxes[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]

    keep: list[int] = []
    while order.size > 0:
        index = int(order[0])
        keep.append(index)
        if order.size == 1:
            break

        rest = order[1:]
        inter_x1 = np.maximum(x1[index], x1[rest])
        inter_y1 = np.maximum(y1[index], y1[rest])
        inter_x2 = np.minimum(x2[index], x2[rest])
        inter_y2 = np.minimum(y2[index], y2[rest])
        inter_w = np.maximum(0.0, inter_x2 - inter_x1)
        inter_h = np.maximum(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        iou = inter_area / (areas[index] + areas[rest] - inter_area + 1e-6)
        order = rest[iou <= iou_threshold]

    return keep


# ---------------------------------------------------------------------------
# ArcFace alignment
# ---------------------------------------------------------------------------

def _estimate_affine(src_pts: np.ndarray, dst_pts: np.ndarray) -> np.ndarray:
    """Estimate 2×3 affine matrix from src_pts → dst_pts (least squares)."""
    n = src_pts.shape[0]
    # Build coefficient matrix: each point contributes 2 equations
    A = np.zeros((2 * n, 6), dtype=np.float64)
    b = np.zeros(2 * n, dtype=np.float64)
    for i in range(n):
        x, y = float(src_pts[i, 0]), float(src_pts[i, 1])
        A[2 * i] = [x, y, 1, 0, 0, 0]
        A[2 * i + 1] = [0, 0, 0, x, y, 1]
        b[2 * i] = float(dst_pts[i, 0])
        b[2 * i + 1] = float(dst_pts[i, 1])
    params, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    M = np.array([[params[0], params[1], params[2]],
                  [params[3], params[4], params[5]]], dtype=np.float32)
    return M


def _warp_affine(image: np.ndarray, M: np.ndarray, out_size: int) -> np.ndarray:
    """Apply affine transform M to image, output out_size × out_size RGB."""
    from PIL import Image as PILImage

    height, width = image.shape[:2]
    pil_img = PILImage.fromarray(image)

    # PIL uses inverse transform: we need M_inv
    M_inv = np.linalg.pinv(np.vstack([M, [0, 0, 1]]))[:2]

    # Use PIL AFFINE transform (inverse map)
    a, b_coef, c, d, e, f = M_inv.ravel()[:6]
    transformed = pil_img.transform(
        (out_size, out_size),
        PILImage.AFFINE,
        (a, b_coef, c, d, e, f),
        PILImage.BILINEAR,
    )
    return np.array(transformed, dtype=np.uint8)


def _align_face(image: np.ndarray, landmarks: list[list[float]], out_size: int) -> np.ndarray:
    """Align face to canonical landmarks for ArcFace / genderage input."""
    src_pts = np.array(landmarks, dtype=np.float32)  # (5, 2)
    if out_size != 112:
        dst_pts = _ARCFACE_DST * (out_size / 112.0)
    else:
        dst_pts = _ARCFACE_DST
    M = _estimate_affine(src_pts, dst_pts)
    return _warp_affine(image, M, out_size)


def _make_arcface_blob(face_112: np.ndarray) -> np.ndarray:
    """112×112 RGB → ArcFace input blob (1, 3, 112, 112) float32."""
    blob = (face_112.astype(np.float32) - 127.5) / 128.0
    return np.transpose(blob, (2, 0, 1))[np.newaxis, :]


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    flat = vector.astype(np.float32).reshape(-1)
    norm = float(np.linalg.norm(flat))
    return flat if norm == 0.0 else flat / norm


# ---------------------------------------------------------------------------
# genderage (age / gender)
# ---------------------------------------------------------------------------

def _decode_age_gender(output: np.ndarray) -> tuple[int, str]:
    """Decode genderage model output → (age, gender_label)."""
    out = output.reshape(-1)
    # InsightFace genderage outputs: [gender_score, age_normalized]
    # gender: >=0.5 = female, age = int(age_norm * 100)
    if out.shape[0] >= 2:
        gender = "f" if float(out[0]) >= 0.5 else "m"
        age = int(np.clip(out[1] * 100.0, 0, 120))
    else:
        gender = "m"
        age = 0
    return age, gender


# ---------------------------------------------------------------------------
# Public FaceEngine implementation
# ---------------------------------------------------------------------------

class BuffaloLEngine:
    """FaceEngine backed by InsightFace buffalo_l (ONNX Runtime).

    Paths of the three model files are resolved from the model_dir at init;
    sessions are managed by the global session_manager (lazy load + eviction).
    """

    def __init__(self, model_dir: str) -> None:
        base = Path(model_dir)
        self._det_path = str(base / "det_10g.onnx")
        self._rec_path = str(base / "w600k_r50.onnx")
        self._age_gender_path = str(base / "genderage.onnx")

    def embed_crop(self, image: np.ndarray) -> np.ndarray | None:
        """Compute ArcFace embedding for an image that IS a face crop (no detection).

        Resizes directly to 112×112 and runs the recognition model. Used for
        manual_original face imports where no detection step is needed.
        """
        from PIL import Image as PILImage

        from photofant.inference.session_manager import session_manager

        try:
            pil = PILImage.fromarray(image).convert("RGB").resize((112, 112), PILImage.BILINEAR)
            face_112 = np.array(pil, dtype=np.uint8)
            blob = _make_arcface_blob(face_112)

            rec_session = session_manager.acquire_session(self._rec_path)
            try:
                rec_input_name = rec_session.get_inputs()[0].name
                rec_output_name = rec_session.get_outputs()[0].name
                raw = rec_session.run([rec_output_name], {rec_input_name: blob})[0]
            finally:
                session_manager.release_session(self._rec_path)

            return _l2_normalize(raw).astype(np.float32)
        except Exception:
            log.exception("embed_crop failed")
            return None

    def detect(self, image: np.ndarray) -> list[dict]:
        """Return one dict per face: {bbox, score, age, embedding, landmarks}."""
        from photofant.inference.session_manager import session_manager

        blob, scale = _make_scrfd_blob(image)
        input_height, input_width = image.shape[:2]

        # --- detection ---
        det_session = session_manager.acquire_session(self._det_path)
        try:
            input_name = det_session.get_inputs()[0].name
            output_names = [o.name for o in det_session.get_outputs()]
            raw_outputs = det_session.run(output_names, {input_name: blob})
            det_outputs = dict(zip(output_names, raw_outputs, strict=True))
        finally:
            session_manager.release_session(self._det_path)

        face_dicts = _decode_scrfd_outputs(
            det_outputs, _DET_INPUT_SIZE, _DET_INPUT_SIZE, scale,
        )
        if not face_dicts:
            return []

        # --- embedding + age for each detected face ---
        rec_session = session_manager.acquire_session(self._rec_path)
        age_session = session_manager.acquire_session(self._age_gender_path)
        try:
            rec_input_name = rec_session.get_inputs()[0].name
            rec_output_name = rec_session.get_outputs()[0].name
            age_input_name = age_session.get_inputs()[0].name
            age_output_name = age_session.get_outputs()[0].name

            for face in face_dicts:
                landmarks = face.get("landmarks")
                if landmarks is None:
                    face["embedding"] = None
                    face["age"] = None
                    continue

                # ArcFace embedding (112×112)
                aligned_112 = _align_face(image, landmarks, out_size=112)
                arc_blob = _make_arcface_blob(aligned_112)
                embedding_raw = rec_session.run([rec_output_name], {rec_input_name: arc_blob})[0]
                face["embedding"] = _l2_normalize(embedding_raw).astype(np.float32)

                # Age estimation (96×96, same alignment scaled down)
                aligned_64 = _align_face(image, landmarks, out_size=96)
                age_blob = _make_arcface_blob(aligned_64[:, :, :])  # same norm
                age_raw = age_session.run([age_output_name], {age_input_name: age_blob})[0]
                face["age"], _ = _decode_age_gender(age_raw)

        finally:
            session_manager.release_session(self._rec_path)
            session_manager.release_session(self._age_gender_path)

        return face_dicts


def resolve_buffalo_l() -> BuffaloLEngine | None:
    """Return BuffaloLEngine if model is enabled in registry; None otherwise."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=_MANIFEST_ID, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.info("buffalo_l not enabled or has no path — face detection skipped")
            return None
        model_dir = entry.path

    return BuffaloLEngine(model_dir=model_dir)
