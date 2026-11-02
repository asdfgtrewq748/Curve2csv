"""Five fixed synthetic charts. Assert metric ranges, not pixel identity."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from benchmarks.generator.render import render_sample
from benchmarks.generator.spec import make_spec
from benchmarks.metrics import score_sample
from curve2csv.api import extract
from curve2csv.types import AxesOverride, TickInput


def _run(split_index: int, tmp_path: Path) -> dict[str, object]:
    spec = make_spec("dev", split_index, 20261025)
    document = render_sample(spec, tmp_path)
    axes = document["axes"]
    override = AxesOverride(
        x_ticks=tuple(
            TickInput(px=t["px"], py=t["py"], value=t["value"]) for t in axes["x"]["ticks"]
        ),
        y_ticks=tuple(
            TickInput(px=t["px"], py=t["py"], value=t["value"]) for t in axes["y"]["ticks"]
        ),
        source="sidecar",
    )
    result = extract(tmp_path / "img.png", axes=override)
    return score_sample(document, result, 0.0)


def test_single_line(tmp_path: Path) -> None:
    row = _run(0, tmp_path)
    assert row["chart_type"] == "line"
    assert float(row["plot_area_iou"]) >= 0.95
    assert row["curve_nrmse_range"] is not None
    assert float(row["curve_nrmse_range"]) <= 3.0


def test_multi_line(tmp_path: Path) -> None:
    row = _run(1, tmp_path)
    assert int(row["n_series_gt"]) >= 2
    assert float(row["plot_area_iou"]) >= 0.95
    assert float(row["series_match_acc"]) >= 0.9


def test_line_with_markers(tmp_path: Path) -> None:
    row = _run(9, tmp_path)
    assert row["chart_type"] == "line+marker"
    assert float(row["plot_area_iou"]) >= 0.9


def test_scatter(tmp_path: Path) -> None:
    row = _run(18, tmp_path)
    assert row["chart_type"] == "scatter"
    assert float(row["plot_area_iou"]) >= 0.95
    assert int(row["n_series_pred"]) >= 1


def test_bar(tmp_path: Path) -> None:
    row = _run(27, tmp_path)
    assert row["chart_type"] == "bar"
    assert float(row["plot_area_iou"]) >= 0.95
    assert row["bar_rel_err"] is not None
    assert float(row["bar_rel_err"]) <= 0.02
    assert np.isfinite(float(row["bar_rel_err"]))
