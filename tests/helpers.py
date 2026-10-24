"""Small matplotlib figures shared by the unit tests."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import NDArray

from curve2csv.types import AxesOverride, TickInput


def _grab(fig: Figure, ax: Axes) -> tuple[NDArray[np.uint8], AxesOverride]:
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    image = np.ascontiguousarray(rgba[:, :, :3])
    height = image.shape[0]
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    def image_xy(data_x: float, data_y: float) -> tuple[float, float]:
        px, py = ax.transData.transform((data_x, data_y))
        return float(px), float(height - py)

    def ticks(values: list[float], *, vertical: bool) -> tuple[TickInput, ...]:
        items: list[TickInput] = []
        for value in values:
            if vertical:
                px, py = image_xy(float(xlim[0]), float(value))
            else:
                px, py = image_xy(float(value), float(ylim[0]))
            items.append(TickInput(px=px, py=py, value=float(value)))
        return tuple(items)

    x_values = [float(v) for v in ax.get_xticks() if xlim[0] <= float(v) <= xlim[1]]
    y_values = [float(v) for v in ax.get_yticks() if ylim[0] <= float(v) <= ylim[1]]
    if len(x_values) < 2:
        x_values = [float(xlim[0]), float(xlim[1])]
    if len(y_values) < 2:
        y_values = [float(ylim[0]), float(ylim[1])]
    axes = AxesOverride(
        x_ticks=ticks(x_values, vertical=False), y_ticks=ticks(y_values, vertical=True)
    )
    return image, axes


def save_image(path: Path, image: NDArray[np.uint8]) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(path)


def line_figure(
    x: NDArray[np.float64],
    series: list[tuple[NDArray[np.float64], str]],
    *,
    occlude: tuple[float, float] | None = None,
) -> tuple[NDArray[np.uint8], AxesOverride]:
    fig, ax = plt.subplots(figsize=(5.0, 3.2), dpi=100)
    for y, color in series:
        ax.plot(x, y, color=color, lw=1.6)
    if occlude is not None:
        lo, hi = occlude
        y0, y1 = ax.get_ylim()
        ax.axvspan(lo, hi, color="white", zorder=5)
        ax.text(
            (lo + hi) / 2.0,
            (y0 + y1) / 2.0,
            "note",
            ha="center",
            va="center",
            color="black",
            zorder=6,
        )
    image, axes = _grab(fig, ax)
    plt.close(fig)
    return image, axes


def scatter_figure() -> (
    tuple[NDArray[np.uint8], AxesOverride, NDArray[np.float64], NDArray[np.float64]]
):
    rng = np.random.Generator(np.random.PCG64(7))
    x = np.linspace(0.0, 10.0, 12)
    y = rng.uniform(0.2, 0.8, size=12)
    fig, ax = plt.subplots(figsize=(5.0, 3.2), dpi=100)
    ax.scatter(x, y, c="#1f77b4", s=40, marker="o")
    image, axes = _grab(fig, ax)
    plt.close(fig)
    return image, axes, x, y


def bar_figure() -> tuple[NDArray[np.uint8], AxesOverride, NDArray[np.float64]]:
    heights = np.array([1.0, 2.5, 1.7, 3.2], dtype=np.float64)
    fig, ax = plt.subplots(figsize=(5.0, 3.2), dpi=100)
    ax.bar(np.arange(len(heights)), heights, color="#2ca02c", width=0.6)
    image, axes = _grab(fig, ax)
    plt.close(fig)
    return image, axes, heights
