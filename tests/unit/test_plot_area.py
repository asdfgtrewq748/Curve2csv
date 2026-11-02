"""Plot-area IoU on a synthetic figure, and abstain on a blank image."""

from __future__ import annotations

import numpy as np

from benchmarks.generator.render import render_sample
from benchmarks.generator.spec import make_spec
from curve2csv.config import PipelineConfig
from curve2csv.detect.plot_area import detect_plot_area
from curve2csv.types import Abstain, PlotArea


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / union if union else 0.0


def test_synthetic_line_iou(tmp_path) -> None:
    spec = make_spec("dev", 0, 20261025)
    document = render_sample(spec, tmp_path)
    image = np.asarray(__import__("PIL").Image.open(tmp_path / "img.png"))
    area = detect_plot_area(image, PipelineConfig())
    assert isinstance(area, PlotArea)
    assert _iou(area.bbox, tuple(document["plot_area"]["bbox"])) >= 0.95


def test_blank_image_abstains() -> None:
    blank = np.full((90, 120, 3), 255, dtype=np.uint8)
    area = detect_plot_area(blank, PipelineConfig())
    assert isinstance(area, Abstain)
    assert area.reason == "no_axis_found"
