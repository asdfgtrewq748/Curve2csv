"""Color-constrained paths bridge only a short hole under another series."""

from __future__ import annotations

import numpy as np

from curve2csv.extract.track import OCCLUSION_SLACK_PX, track_series
from curve2csv.types import DataPoint, PointFlag, Series


def _stroke(length: int = 40, y: int = 20, gap: tuple[int, int] | None = None) -> np.ndarray:
    mask = np.zeros((60, length + 20), dtype=bool)
    mask[y : y + 3, 5 : 5 + length] = True
    if gap is not None:
        mask[y : y + 3, gap[0] : gap[1]] = False
    return mask


def test_plain_gap_is_not_bridged() -> None:
    mask = _stroke(gap=(30, 40))
    nodes = track_series(
        mask,
        (0, 0, mask.shape[1], mask.shape[0]),
        est_width=3.0,
        thin_width=3.0,
        color_lab=None,
        lab_image=None,
        other_mask=None,
    )
    assert nodes
    assert all(node.kind == "ink" for node in nodes)
    assert OCCLUSION_SLACK_PX == 2


def test_short_crossing_is_bridged_and_a_wider_hole_is_not() -> None:
    mask = _stroke(length=70, gap=(40, 43))
    other = np.zeros_like(mask)
    other[5:50, 40:43] = True
    bbox = (0, 0, mask.shape[1], mask.shape[0])
    nodes = track_series(
        mask,
        bbox,
        est_width=3.0,
        thin_width=3.0,
        color_lab=None,
        lab_image=None,
        other_mask=other,
    )
    bridges = [node for node in nodes if node.kind == "bridge"]
    assert [node.col for node in bridges] == [40, 41, 42]
    assert bridges[0].py == bridges[-1].py

    wide = _stroke(length=70, gap=(40, 48))
    wide_other = np.zeros_like(wide)
    wide_other[5:50, 40:48] = True
    wide_nodes = track_series(
        wide,
        (0, 0, wide.shape[1], wide.shape[0]),
        est_width=3.0,
        thin_width=3.0,
        color_lab=None,
        lab_image=None,
        other_mask=wide_other,
    )
    assert all(node.kind == "ink" for node in wide_nodes)


def test_path_stays_on_the_series_color() -> None:
    mask = np.zeros((80, 90), dtype=bool)
    mask[15:18, 5:80] = True
    mask[45:48, 30:55] = True
    lab = np.zeros((80, 90, 3), dtype=np.float64)
    lab[:, :] = (50.0, 0.0, 0.0)
    lab[15:18, :] = (50.0, 40.0, 0.0)
    lab[45:48, :] = (50.0, -40.0, 0.0)
    nodes = track_series(
        mask,
        (0, 0, 90, 80),
        est_width=3.0,
        thin_width=3.0,
        color_lab=(50.0, 40.0, 0.0),
        lab_image=lab,
        other_mask=None,
    )
    assert nodes
    assert all(node.kind == "ink" for node in nodes)
    assert all(14.0 < node.py < 20.0 for node in nodes)


def test_strict_score_drops_interpolated_points() -> None:
    from benchmarks.real.metrics import valid_xy

    series = Series(
        series_id="s0",
        kind="line",
        label=None,
        color_hex=None,
        points=[
            DataPoint(0.0, 1.0, 1.5, 2.5, 0.9, PointFlag.NONE),
            DataPoint(1.0, 1.0, 2.5, 2.5, 0.55, PointFlag.INTERPOLATED),
            DataPoint(2.0, 1.0, 3.5, 2.5, 0.9, PointFlag.AMBIGUOUS_SERIES),
        ],
        gaps=[],
        coverage=1.0,
        confidence=0.9,
    )
    strict = valid_xy(series)
    bridged = valid_xy(series, include_interpolated=True)
    assert strict.shape == (1, 2)
    assert bridged.shape == (2, 2)
    assert float(bridged[1, 0]) == 1.0
