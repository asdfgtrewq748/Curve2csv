"""Report-only evidence metrics: ink support and fabrication reconciliation."""

from __future__ import annotations

import numpy as np
from tests.helpers import line_figure

from benchmarks.metrics import aggregate, ink_support
from curve2csv.api import extract
from curve2csv.types import (
    SCHEMA_VERSION,
    DataPoint,
    ExtractionResult,
    LoadedImage,
    PlotArea,
    PointFlag,
    Series,
)


def test_ink_support_on_extracted_line() -> None:
    x = np.linspace(0.0, 5.0, 120)
    image, axes = line_figure(x, [(0.3 * x, "#1f77b4")])
    result = extract(image, axes=axes)
    support = ink_support(result)
    expected = sum(
        1
        for series in result.series
        for point in series.points
        if point.status not in {"empty", "bridge"}
    )
    assert support["n_checked"] == expected
    assert expected > 0
    fraction = support["fraction"]
    assert fraction is not None and float(fraction) >= 0.9


def test_ink_support_excludes_bridge_and_empty_points() -> None:
    rgb = np.full((20, 20, 3), 255, dtype=np.uint8)
    rgb[5, 5] = (31, 119, 180)
    result = ExtractionResult(
        schema_version=SCHEMA_VERSION,
        source=LoadedImage(rgb=rgb, source="memory", sha256="0"),
        plot_area=PlotArea((0, 0, 20, 20), 20.0, 0.0, 1.0),
        calibration={},
        series=[
            Series(
                series_id="s0",
                kind="line",
                label=None,
                color_hex="#1f77b4",
                points=[
                    DataPoint(0.0, 0.0, 5.5, 5.5, 0.9, PointFlag.NONE),
                    DataPoint(1.0, 0.0, 15.5, 15.5, 0.55, PointFlag.INTERPOLATED),
                    DataPoint(None, None, 16.5, 16.5, 0.1, PointFlag.LOW_CONFIDENCE),
                ],
                gaps=[],
                coverage=1.0,
                confidence=0.9,
            )
        ],
        image_confidence=0.9,
        abstentions=[],
        config_hash="test",
    )
    support = ink_support(result)
    assert support["n_checked"] == 1
    assert support["n_supported"] == 1
    assert support["fraction"] == 1.0


def test_fabrication_aggregate_is_the_row_sum() -> None:
    def row(identifier: str, fabrication: int, support: float) -> dict[str, object]:
        return {
            "id": identifier,
            "chart_type": "line",
            "degradation": "clean",
            "series_bucket": "1",
            "occluded": False,
            "markers_overlap": False,
            "color_mode": "tab10",
            "n_series_gt": 1,
            "domain_shape": "peaks",
            "point_confidence": np.asarray([0.9], dtype=np.float64),
            "point_error": np.asarray([False]),
            "point_flagged": np.asarray([False]),
            "fabrication_count": fabrication,
            "bridged_count": 1,
            "ink_support_fraction": support,
            "ink_support_checked": 10,
            "curve_nrmse_range": 1.0,
            "x_coverage": 1.0,
            "plot_area_iou": 1.0,
            "axis_calib_rel_err": 0.0,
            "false_point_rate": 0.0,
            "series_match_acc": 1.0,
            "scatter_f1": None,
            "bar_rel_err": None,
            "runtime_s": 1.0,
            "width": 100,
            "height": 100,
            "completeness": 1.0,
        }

    rows = [row("a", 2, 0.9), row("b", 3, 0.5)]
    summary = aggregate(rows)
    assert summary["fabrication_count"] == 5
    assert summary["fabrication_count"] == sum(int(item["fabrication_count"]) for item in rows)
    assert summary["bridged_count"] == 2
    assert summary["ink_support_median"] == 0.7
    assert summary["ink_support_checked"] == 20
