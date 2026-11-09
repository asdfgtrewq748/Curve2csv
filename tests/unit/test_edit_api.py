"""Human-confirm edits and honest gap/segment export fields."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from tests.helpers import line_figure

from curve2csv.api import (
    clear_range,
    confirm_axis_calibration,
    confirm_plot_box,
    extract,
    pick_series,
    trace_stroke,
)
from curve2csv.errors import InputError
from curve2csv.io.export import write_csv, write_json
from curve2csv.types import (
    SCHEMA_VERSION,
    AxesOverride,
    DataPoint,
    ExtractionResult,
    LoadedImage,
    PlotArea,
    PointFlag,
    Series,
)


def _one_line() -> tuple[np.ndarray, AxesOverride]:
    x = np.linspace(0.0, 10.0, 240)
    return line_figure(x, [(0.4 * x, "#1f77b4")])


def _blank_evidence_result() -> ExtractionResult:
    return ExtractionResult(
        schema_version=SCHEMA_VERSION,
        source=LoadedImage(rgb=np.zeros((20, 20, 3), dtype=np.uint8), source="memory", sha256="0"),
        plot_area=PlotArea((0, 0, 20, 20), 20.0, 0.0, 1.0),
        calibration={},
        series=[
            Series(
                series_id="s0",
                kind="line",
                label=None,
                color_hex="#1f77b4",
                points=[
                    DataPoint(1.0, 2.0, 1.5, 1.5, 0.9, PointFlag.NONE, segment_id=0),
                    DataPoint(None, None, 2.5, 1.5, 0.2, PointFlag.LOW_CONFIDENCE, segment_id=1),
                    DataPoint(3.0, 2.0, 3.5, 1.5, 0.55, PointFlag.INTERPOLATED, segment_id=2),
                ],
                gaps=[(2.0, 3.0)],
                coverage=0.8,
                confidence=0.7,
            )
        ],
        image_confidence=0.7,
        abstentions=[],
        config_hash="test",
    )


def test_export_carries_status_segment_and_calibration_id(tmp_path: Path) -> None:
    result = _blank_evidence_result()
    csv_path = tmp_path / "edit.csv"
    json_path = tmp_path / "edit.json"
    write_csv(result, csv_path)
    write_json(result, json_path)
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["status"] for row in rows] == ["ok", "empty", "bridge"]
    assert [row["segment_id"] for row in rows] == ["0", "1", "2"]
    assert all(row["calibration_id"] == result.calibration_id for row in rows)
    assert rows[1]["x"] == "" and rows[1]["y"] == ""
    assert rows[2]["interpolated"] == "1"

    document = json.loads(json_path.read_text(encoding="utf-8"))
    schema_path = (
        Path(__import__("curve2csv").__file__).resolve().parent / "schema" / "result.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(document, schema)
    series = document["series"][0]
    assert document["calibration_id"] == result.calibration_id
    assert [point["status"] for point in series["points"]] == ["ok", "empty", "bridge"]
    assert [segment["segment_id"] for segment in series["segments"]] == [0, 1, 2]
    assert series["segments"][2]["n_bridged"] == 1


def test_confirm_plot_box_keeps_calibration() -> None:
    image, axes = _one_line()
    result = extract(image, axes=axes)
    assert isinstance(result.plot_area, PlotArea)
    rerun = confirm_plot_box(result, result.plot_area.bbox)
    assert isinstance(rerun.plot_area, PlotArea)
    assert rerun.plot_area.source == "manual:plot_box"
    assert rerun.calibration_id == result.calibration_id
    assert len(rerun.series) == len(result.series)

    direct = extract(image, axes=axes, plot_box=result.plot_area.bbox)
    assert isinstance(direct.plot_area, PlotArea)
    assert direct.plot_area.source == "manual:plot_box"
    assert direct.calibration_id == result.calibration_id


def test_confirm_axis_calibration_changes_id_and_source() -> None:
    image, axes = _one_line()
    result = extract(image, axes=axes)
    confirmed = AxesOverride(
        x_ticks=axes.x_ticks,
        y_ticks=axes.y_ticks,
        x_scale=axes.x_scale,
        y_scale=axes.y_scale,
        source="manual:confirmed",
    )
    rerun = confirm_axis_calibration(result, confirmed)
    x_cal = rerun.calibration["x"]
    assert getattr(x_cal, "source", None) == "manual:confirmed"
    assert rerun.calibration_id != result.calibration_id
    assert isinstance(result.plot_area, PlotArea)
    assert isinstance(rerun.plot_area, PlotArea)
    assert rerun.plot_area.bbox == result.plot_area.bbox


def test_pick_series_by_click_and_stroke() -> None:
    x = np.linspace(0.0, 10.0, 240)
    image, axes = line_figure(x, [(0.2 * x, "#1f77b4"), (0.2 * x + 2.0, "#ff7f0e")])
    result = extract(image, axes=axes)
    assert len(result.series) >= 2
    first = result.series[0]
    sample = first.points[len(first.points) // 2]
    picked = pick_series(result, (sample.px, sample.py))
    assert [series.series_id for series in picked.series] == [first.series_id]

    centers = [
        (series.points[len(series.points) // 2].px, series.points[len(series.points) // 2].py)
        for series in result.series[:2]
    ]
    stroked = pick_series(result, centers, radius=8.0)
    assert {series.series_id for series in stroked.series} == {
        series.series_id for series in result.series[:2]
    }


def test_clear_range_leaves_empty_and_does_not_interpolate(tmp_path: Path) -> None:
    image, axes = _one_line()
    result = extract(image, axes=axes)
    series = result.series[0]
    before = [
        point for point in series.points if point.x is not None and 4.0 <= float(point.x) <= 6.0
    ]
    assert before
    cleared = clear_range(result, 4.0, 6.0, out=tmp_path)
    series = cleared.series[0]
    for point in series.points:
        if point.x is None:
            mapped = cleared.pixel_to_data(point.px, point.py)
            if mapped is not None and 4.0 <= mapped[0] <= 6.0:
                assert point.status == "empty"
                assert PointFlag.MANUAL in point.flags
                assert PointFlag.INTERPOLATED not in point.flags
        else:
            assert not (4.0 <= float(point.x) <= 6.0)
    assert any(lo <= 4.0 and hi >= 6.0 for lo, hi in series.gaps)
    assert series.coverage < 0.95

    with (tmp_path / "extraction.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    cleared_rows = [row for row in rows if row["status"] == "empty"]
    assert cleared_rows
    assert all(row["x"] == "" and row["y"] == "" for row in cleared_rows)
    assert all(row["interpolated"] == "0" for row in cleared_rows)


def test_clear_range_rejects_unknown_series() -> None:
    image, axes = _one_line()
    result = extract(image, axes=axes)
    with pytest.raises(InputError):
        clear_range(result, 1.0, 2.0, series_id="missing")


def test_trace_stroke_recovers_cleared_segment(tmp_path: Path) -> None:
    image, axes = _one_line()
    result = extract(image, axes=axes)
    cleared = clear_range(result, 4.0, 6.0)
    series_before = cleared.series[0]
    assert series_before.coverage < 0.95

    p4 = next(p for p in result.series[0].points if p.x is not None and 3.7 <= float(p.x) <= 4.0)
    p6 = next(p for p in result.series[0].points if p.x is not None and 6.0 <= float(p.x) <= 6.3)
    traced = trace_stroke(cleared, [(p4.px, p4.py), (p6.px, p6.py)], radius=8.0, out=tmp_path)
    series_after = traced.series[0]
    recovered = [p for p in series_after.points if p.x is not None and 4.2 <= float(p.x) <= 5.8]
    assert len(recovered) > 5
    for p in recovered:
        assert p.status == "ok"
        assert PointFlag.MANUAL in p.flags
    assert series_after.coverage > series_before.coverage
    assert series_after.coverage >= 0.90

    with (tmp_path / "extraction.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    recovered_rows = [row for row in rows if row["x"] and 4.2 <= float(row["x"]) <= 5.8]
    assert recovered_rows
    assert all(row["status"] == "ok" for row in recovered_rows)
    assert all("MANUAL" in row["flags"] for row in recovered_rows)


def test_trace_stroke_abstains_on_blank_background() -> None:
    image, axes = _one_line()
    result = extract(image, axes=axes)
    n_before = sum(len(s.points) for s in result.series)
    # Stroke in pure white background near top of the plot
    area = result.plot_area
    assert isinstance(area, PlotArea)
    top_y = float(area.bbox[1] + 5)
    traced = trace_stroke(
        result,
        [(float(area.bbox[0] + 10), top_y), (float(area.bbox[2] - 10), top_y)],
        radius=4.0,
    )
    n_after = sum(len(s.points) for s in traced.series)
    assert n_after == n_before


def test_trace_stroke_creates_new_series_when_far() -> None:
    x = np.linspace(0.0, 10.0, 240)
    image, axes = line_figure(x, [(0.2 * x, "#1f77b4"), (0.2 * x + 2.0, "#ff7f0e")])
    result = extract(image, axes=axes)
    assert len(result.series) >= 2
    # Keep only the first series
    first = result.series[0]
    sample = first.points[len(first.points) // 2]
    picked = pick_series(result, (sample.px, sample.py))
    assert len(picked.series) == 1

    # Second series sample
    second = result.series[1]
    s_start = second.points[10]
    s_end = second.points[-10]
    traced = trace_stroke(
        picked,
        [(s_start.px, s_start.py), (s_end.px, s_end.py)],
        radius=6.0,
        snap_series_px=4.0,
    )
    assert len(traced.series) == 2
    new_s = traced.series[-1]
    assert new_s.kind == "line"
    assert len(new_s.points) > 10
    assert any(PointFlag.MANUAL in p.flags for p in new_s.points)


def test_trace_stroke_validations() -> None:
    image, axes = _one_line()
    result = extract(image, axes=axes)
    with pytest.raises(InputError, match="radius must be positive"):
        trace_stroke(result, [(10.0, 10.0), (20.0, 20.0)], radius=-1.0)
    with pytest.raises(InputError, match="requires at least 2 stroke points"):
        trace_stroke(result, [(10.0, 10.0)])
    with pytest.raises(InputError, match="no series with id missing"):
        trace_stroke(result, [(10.0, 10.0), (20.0, 20.0)], series_id="missing")
