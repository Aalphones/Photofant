from __future__ import annotations

import pytest
from PIL import Image

from photofant.media.ops import apply_op, is_orientation_only, transform_bbox

# ── is_orientation_only ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("steps", "expected"),
    [
        ([], False),
        ([{"op": "rotate", "params_dict": {"dir": "cw"}}], True),
        ([{"op": "mirror", "params_dict": {"axis": "h"}}], True),
        (
            [
                {"op": "rotate", "params_dict": {"dir": "cw"}},
                {"op": "mirror", "params_dict": {"axis": "v"}},
            ],
            True,
        ),
        ([{"op": "rotate", "params_dict": {"dir": "free", "angle": 12.0}}], False),
        ([{"op": "crop", "params_dict": {"x": 0, "y": 0, "w": 50, "h": 50}}], False),
        (
            [
                {"op": "rotate", "params_dict": {"dir": "cw"}},
                {"op": "crop", "params_dict": {"x": 0, "y": 0, "w": 50, "h": 50}},
            ],
            False,
        ),
    ],
)
def test_is_orientation_only(steps: list[dict[str, object]], expected: bool) -> None:
    assert is_orientation_only(steps) is expected


# ── transform_bbox: single steps against hand-derived geometry ───────────

_BBOX = {"x1": 10.0, "y1": 5.0, "x2": 30.0, "y2": 20.0}
_SIZE = (100, 50)  # width, height


def test_transform_bbox_rotate_cw() -> None:
    result = transform_bbox(_BBOX, [{"op": "rotate", "params_dict": {"dir": "cw"}}], _SIZE)
    assert result == {"x1": 30.0, "y1": 10.0, "x2": 45.0, "y2": 30.0}


def test_transform_bbox_rotate_ccw() -> None:
    result = transform_bbox(_BBOX, [{"op": "rotate", "params_dict": {"dir": "ccw"}}], _SIZE)
    assert result == {"x1": 5.0, "y1": 70.0, "x2": 20.0, "y2": 90.0}


def test_transform_bbox_rotate_180() -> None:
    result = transform_bbox(_BBOX, [{"op": "rotate", "params_dict": {"dir": "180"}}], _SIZE)
    assert result == {"x1": 70.0, "y1": 30.0, "x2": 90.0, "y2": 45.0}


def test_transform_bbox_mirror_h() -> None:
    result = transform_bbox(_BBOX, [{"op": "mirror", "params_dict": {"axis": "h"}}], _SIZE)
    assert result == {"x1": 70.0, "y1": 5.0, "x2": 90.0, "y2": 20.0}


def test_transform_bbox_mirror_v() -> None:
    result = transform_bbox(_BBOX, [{"op": "mirror", "params_dict": {"axis": "v"}}], _SIZE)
    assert result == {"x1": 10.0, "y1": 30.0, "x2": 30.0, "y2": 45.0}


def test_transform_bbox_chained_steps_track_dimension_swap() -> None:
    """rotate cw swaps width/height — the following mirror must use the new width."""
    steps = [
        {"op": "rotate", "params_dict": {"dir": "cw"}},
        {"op": "mirror", "params_dict": {"axis": "h"}},
    ]
    result = transform_bbox(_BBOX, steps, _SIZE)
    assert result == {"x1": 5.0, "y1": 10.0, "x2": 20.0, "y2": 30.0}


# ── transform_bbox matches apply_op's actual pixel transform ─────────────


def test_transform_bbox_matches_apply_op_pixel_result() -> None:
    """The math in transform_bbox must land on the same region apply_op actually produces."""
    width, height = 40, 20
    marker_box = {"x1": 32.0, "y1": 0.0, "x2": 40.0, "y2": 8.0}  # top-right corner

    img = Image.new("RGB", (width, height), color=(10, 10, 10))
    for x in range(32, 40):
        for y in range(8):
            img.putpixel((x, y), (220, 20, 20))

    rotated = apply_op(img, "rotate", {"dir": "cw"})
    new_bbox = transform_bbox(marker_box, [{"op": "rotate", "params_dict": {"dir": "cw"}}], (width, height))

    center_x = int((new_bbox["x1"] + new_bbox["x2"]) / 2)
    center_y = int((new_bbox["y1"] + new_bbox["y2"]) / 2)
    sample = rotated.getpixel((center_x, center_y))

    assert sample[0] > 150
    assert sample[1] < 80
