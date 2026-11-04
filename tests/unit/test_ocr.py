"""Tick-label parsing and one RapidOCR pass on a labeled figure."""

from __future__ import annotations

import numpy as np
import pytest

from curve2csv.api import extract
from curve2csv.ocr.parse import choose_axis, parse_label
from curve2csv.ocr.read import (
    _expand_glued_years,
    _labels_present,
    _merge_words,
    _raise_top_along_stroke,
    _snap_x_to_ticks,
    _span_from_labels,
    _Word,
    _x_tick_marks,
)
from curve2csv.types import AxisCalibration, AxisScale


def test_parse_plain_units_and_powers() -> None:
    assert parse_label("−0.5") == [(-0.5, "plain")]
    assert parse_label("80 years") == [(80.0, "plain")]
    assert parse_label("2 billion") == [(2e9, "plain")]
    assert parse_label("10³") == [(1000.0, "power10")]
    assert parse_label("1e-3") == [(0.001, "plain")]
    assert parse_label("1,000 ppbv") == [(1000.0, "plain")]
    assert parse_label("1.2 billion ha") == [(1.2e9, "plain")]
    assert parse_label("600,000 BCE") == [(-600000.0, "plain")]
    assert parse_label("803.719BCE") == [(-803719.0, "plain")]
    assert parse_label("796,475BCE") == [(-796475.0, "plain")]
    assert parse_label("30million") == [(3e7, "plain")]
    assert parse_label("1.2 °℃") == [(1.2, "plain")]
    assert parse_label("-0.2°℃") == [(-0.2, "plain")]
    assert parse_label("1.500") == [(1.5, "plain")]
    assert parse_label("3.89%") == [(3.89, "plain")]
    assert parse_label("O years") == [(0.0, "plain")]
    assert parse_label("D") == [(0.0, "plain")]
    assert parse_label("5 AD") == [(5.0, "plain")]
    readings = {kind: value for value, kind in parse_label("101")}
    assert readings["plain"] == 101.0
    assert readings["power10"] == 10.0


def test_concatenated_powers_are_log() -> None:
    labels = [(0.0, "100"), (10.0, "101"), (20.0, "102"), (30.0, "103")]
    chosen = choose_axis(labels, vertical=False)
    assert chosen is not None
    pairs, scale = chosen
    assert scale is AxisScale.LOG10
    assert [value for _pos, value in pairs] == [1.0, 10.0, 100.0, 1000.0]


def test_one_outlier_tick_is_dropped() -> None:
    labels = [(0.0, "0"), (10.0, "1"), (20.0, "2"), (30.0, "3"), (40.0, "99")]
    chosen = choose_axis(labels, vertical=False)
    assert chosen is not None
    pairs, scale = chosen
    assert scale is AxisScale.LINEAR
    assert [value for _pos, value in pairs] == [0.0, 1.0, 2.0, 3.0]


def test_glued_year_token_splits() -> None:
    words = [
        _Word("1958", 1.0, 71.0, 546.0, 54.0, 89.0, 536.0, 556.0),
        _Word("2010", 1.0, 660.0, 546.0, 641.0, 679.0, 536.0, 556.0),
        _Word("20202025", 1.0, 796.5, 545.5, 757.0, 836.0, 536.0, 555.0),
    ]
    texts = [word.text for word in _expand_glued_years(words)]
    assert texts == ["1958", "2010", "2020", "2025"]


def test_missing_axis_row_asks_for_a_margin_pass() -> None:
    years = [
        _Word("1980", 1.0, 180.0, 520.0, 160.0, 200.0, 510.0, 530.0),
        _Word("2000", 1.0, 500.0, 520.0, 480.0, 520.0, 510.0, 530.0),
    ]
    assert _labels_present(years, 850, 600) == (False, True)
    extra = [_Word("6", 0.9, 20.0, 110.0, 16.0, 24.0, 104.0, 116.0)]
    merged = _merge_words(years, extra + years[:1])
    assert [word.text for word in merged] == ["1980", "2000", "6"]


def test_short_spine_does_not_shrink_the_frame() -> None:
    # Labels span the axis. A darker piece of the series covers only the right
    # half. The frame keeps the labels and may grow to a longer spine.
    left, right = _span_from_labels(
        87.0,
        753.0,
        spine_left=461.0,
        spine_right=769.0,
        y_axis=69.0,
    )
    assert left == 69.0
    assert right == 769.0
    left, right = _span_from_labels(80.0, 700.0)
    assert (left, right) == (80.0, 700.0)


def test_x_tick_marks_put_edge_labels_on_the_axis() -> None:
    # Grapher edge-anchors the first and last label, so their centers sit
    # inside the ticks. The marks below the baseline are the true positions.
    gray = np.full((40, 100), 255, dtype=np.uint8)
    for x in (9, 29, 49, 69, 89):
        gray[10:14, x : x + 2] = 100
    marks = _x_tick_marks(gray, bottom=9.0, label_top=20.0)
    assert marks == [9.5, 29.5, 49.5, 69.5, 89.5]
    pairs = [(15.0, 1200.0), (30.0, 1300.0), (50.0, 1400.0), (70.0, 1500.0), (85.0, 1600.0)]
    snapped = _snap_x_to_ticks(pairs, marks)
    assert snapped == [
        (9.5, 1200.0),
        (30.0, 1300.0),
        (50.0, 1400.0),
        (70.0, 1500.0),
        (89.5, 1600.0),
    ]
    # A label row without visible marks stays where OCR put it.
    assert _snap_x_to_ticks(pairs, []) == pairs


def test_stroke_above_the_top_tick_raises_the_frame() -> None:
    rgb = np.full((200, 200, 3), 255, dtype=np.uint8)
    rgb[90:160, 98:102] = (76, 106, 156)
    # A logo above a gap must not pull the frame up to itself.
    rgb[10:18, 40:48] = (76, 106, 156)
    raised = _raise_top_along_stroke(rgb, 40.0, 160.0, 120.0, 50.0)
    assert raised == 90.0
    untouched = _raise_top_along_stroke(rgb, 40.0, 160.0, 170.0, 40.0)
    assert untouched == 170.0


def test_linear_ticks_stay_linear() -> None:
    labels = [(0.0, "0"), (20.0, "5"), (40.0, "10")]
    chosen = choose_axis(labels, vertical=False)
    assert chosen is not None
    pairs, scale = chosen
    assert scale is AxisScale.LINEAR
    assert [value for _pos, value in pairs] == [0.0, 5.0, 10.0]


def test_rapidocr_reads_a_labeled_line(tmp_path) -> None:
    pytest.importorskip("rapidocr_onnxruntime")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.linspace(0.0, 10.0, 40)
    fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=120)
    ax.plot(x, np.sin(x), color="#d62728", lw=2.0)
    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(-1.2, 1.2)
    image_path = tmp_path / "labeled.png"
    fig.savefig(image_path)
    plt.close(fig)
    result = extract(image_path)
    x_cal = result.calibration["x"]
    y_cal = result.calibration["y"]
    assert isinstance(x_cal, AxisCalibration)
    assert isinstance(y_cal, AxisCalibration)
    assert x_cal.source == "ocr"
    assert x_cal.scale is AxisScale.LINEAR
    assert y_cal.scale is AxisScale.LINEAR
    assert result.mapper is not None
    area = result.plot_area
    assert not hasattr(area, "reason")
    x0, y0, x1, y1 = area.bbox  # type: ignore[union-attr]
    left_pt = result.mapper.pixel_to_data(float(x0), float(y1))
    right_pt = result.mapper.pixel_to_data(float(x1), float(y1))
    top_pt = result.mapper.pixel_to_data(float(x0), float(y0))
    assert left_pt is not None and right_pt is not None and top_pt is not None
    left, bottom = left_pt
    right, _bottom = right_pt
    _left, top = top_pt
    assert abs(left - 0.0) <= 0.5
    assert abs(right - 10.0) <= 0.5
    assert abs(bottom - (-1.2)) <= 0.15
    assert abs(top - 1.2) <= 0.15


def test_rapidocr_reads_a_log_axis(tmp_path) -> None:
    pytest.importorskip("rapidocr_onnxruntime")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.logspace(0.0, 3.0, 40)
    fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=120)
    ax.semilogx(x, np.log10(x), color="#1f77b4", lw=2.0)
    ax.set_xlim(1.0, 1000.0)
    ax.set_ylim(0.0, 3.0)
    image_path = tmp_path / "log.png"
    fig.savefig(image_path)
    plt.close(fig)
    result = extract(image_path)
    x_cal = result.calibration["x"]
    y_cal = result.calibration["y"]
    assert isinstance(x_cal, AxisCalibration)
    assert isinstance(y_cal, AxisCalibration)
    assert x_cal.scale is AxisScale.LOG10
    assert y_cal.scale is AxisScale.LINEAR
    assert result.mapper is not None
    area = result.plot_area
    assert not hasattr(area, "reason")
    x0, y0, x1, y1 = area.bbox  # type: ignore[union-attr]
    left_pt = result.mapper.pixel_to_data(float(x0), float(y1))
    right_pt = result.mapper.pixel_to_data(float(x1), float(y0))
    assert left_pt is not None and right_pt is not None
    left, bottom = left_pt
    right, top = right_pt
    assert abs(np.log10(left) - 0.0) <= 0.15
    assert abs(np.log10(right) - 3.0) <= 0.15
    assert abs(bottom - 0.0) <= 0.2
    assert abs(top - 3.0) <= 0.2


def test_rapidocr_reads_labels_without_spines(tmp_path) -> None:
    """Light axes (no spine ink) still calibrate from the tick labels."""

    pytest.importorskip("rapidocr_onnxruntime")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.linspace(0.0, 10.0, 30)
    fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=120)
    ax.plot(x, np.sin(x), color="#d62728", lw=2.5)
    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(-1.2, 1.2)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    for value, frac in ((0, 0.0), (2, 0.2), (4, 0.4), (6, 0.6), (8, 0.8), (10, 1.0)):
        ax.text(
            frac,
            -0.06,
            str(value),
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=11,
            clip_on=False,
        )
    for value, frac in ((-1.2, 0.0), (-0.6, 0.25), (0.0, 0.5), (0.6, 0.75), (1.2, 1.0)):
        ax.text(
            -0.04,
            frac,
            f"{value:.1f}",
            transform=ax.transAxes,
            ha="right",
            va="center",
            fontsize=11,
            clip_on=False,
        )
    fig.tight_layout()
    image_path = tmp_path / "nospine.png"
    fig.savefig(image_path, bbox_inches="tight")
    plt.close(fig)
    result = extract(image_path)
    x_cal = result.calibration["x"]
    y_cal = result.calibration["y"]
    assert isinstance(x_cal, AxisCalibration)
    assert isinstance(y_cal, AxisCalibration)
    assert x_cal.source == "ocr"
    assert result.mapper is not None
    area = result.plot_area
    assert not hasattr(area, "reason")
    x0, y0, x1, y1 = area.bbox  # type: ignore[union-attr]
    left_pt = result.mapper.pixel_to_data(float(x0), float(y1))
    right_pt = result.mapper.pixel_to_data(float(x1), float(y0))
    assert left_pt is not None and right_pt is not None
    left, bottom = left_pt
    right, top = right_pt
    assert abs(left - 0.0) <= 0.15
    assert abs(right - 10.0) <= 0.15
    assert abs(bottom - (-1.2)) <= 0.15
    assert abs(top - 1.2) <= 0.15
