"""A black/grey single curve falls back to one series; blank boxes stay empty."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from numpy.typing import NDArray  # noqa: E402
from tests.helpers import _grab  # noqa: E402

from curve2csv.api import extract  # noqa: E402
from curve2csv.types import AxesOverride, Series  # noqa: E402

_X = np.linspace(0.05, 1.0, 90)
_Y = 0.25 + 0.55 * _X + 0.04 * np.sin(6.0 * _X)


def _chart(
    color: str | None,
    *,
    panel: bool = True,
    legend: bool = False,
) -> tuple[NDArray[np.uint8], AxesOverride]:
    fig, ax = plt.subplots(figsize=(3.4, 2.7), dpi=120)
    if color is not None:
        ax.plot(_X, _Y, color=color, lw=1.4)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.tick_params(direction="in", top=True, right=True, length=5, width=0.8)
    if panel:
        ax.text(
            0.04,
            0.93,
            "(a)",
            transform=ax.transAxes,
            family="serif",
            fontsize=12,
            color="black",
        )
    if legend:
        ax.plot([], [], color=color or "black", lw=1.2, label="sample")
        ax.legend(loc="upper left", frameon=False, fontsize=8)
    image, axes = _grab(fig, ax)
    plt.close(fig)
    return image, axes


def _valid_xy(series: Series) -> NDArray[np.float64]:
    rows = [
        (float(point.x), float(point.y))
        for point in series.points
        if point.status == "ok" and point.x is not None and point.y is not None
    ]
    return np.asarray(rows, dtype=np.float64)


def test_black_curve_with_inward_ticks_text_and_legend_is_one_series() -> None:
    image, axes = _chart("black", panel=True, legend=True)
    result = extract(image, axes=axes)
    assert result.diagnostics.get("achromatic_fallback") is True
    assert len(result.series) == 1
    xy = _valid_xy(result.series[0])
    assert xy.shape[0] >= 40
    order = np.argsort(xy[:, 0])
    px = xy[order, 0]
    py = xy[order, 1]
    sample = np.linspace(0.15, 0.90, 60)
    truth = 0.25 + 0.55 * sample + 0.04 * np.sin(6.0 * sample)
    error = np.abs(np.interp(sample, px, py) - truth)
    assert float(np.median(error)) <= 0.01
    assert float(np.max(error)) <= 0.03
    # The legend sample sits in the upper-left; the curve does not reach there.
    assert float(np.max(py[px < 0.5])) < 0.80


def test_blank_box_with_only_ticks_and_text_returns_no_series() -> None:
    image, axes = _chart(None, panel=True)
    result = extract(image, axes=axes)
    assert result.series == []


def test_colored_curve_stays_on_the_chromatic_path() -> None:
    image, axes = _chart("#d62728", panel=True)
    result = extract(image, axes=axes)
    assert result.diagnostics.get("achromatic_fallback") is False
    assert len(result.series) == 1
    assert result.series[0].color_hex is not None
    xy = _valid_xy(result.series[0])
    assert xy.shape[0] >= 40
    order = np.argsort(xy[:, 0])
    px = xy[order, 0]
    py = xy[order, 1]
    sample = np.linspace(0.15, 0.90, 60)
    truth = 0.25 + 0.55 * sample + 0.04 * np.sin(6.0 * sample)
    assert float(np.max(np.abs(np.interp(sample, px, py) - truth))) <= 0.03
